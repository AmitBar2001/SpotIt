import oci
import os
import concurrent.futures
from fastapi import HTTPException
from datetime import datetime, timedelta
from pathlib import Path
from app.logger import logger
from app.config import settings


# --- Custom Exceptions ---
class S3UploadError(Exception):
    pass


class S3PresignedUrlError(Exception):
    pass


NAMESPACE_NAME = settings.storage_namespace
BUCKET_NAME = settings.storage_bucket_name
CONFIG_FILE_PATH = Path(settings.oci_config_path)

config = oci.config.from_file(file_location=CONFIG_FILE_PATH)
object_storage_client = oci.object_storage.ObjectStorageClient(config)


def _upload_and_create_presigned_url(
    client: oci.object_storage.ObjectStorageClient,
    namespace: str,
    bucket_name: str,
    local_file_path: str,
    object_name: str,
    url_expiration_hours: int,
    as_zip: bool = False,
) -> str | None:
    """
    Helper function to upload a single file and create a presigned URL.
    This function will be executed in a separate thread.
    """
    logger.info(
        f"Uploading file '{local_file_path}' as object '{object_name}' to bucket '{bucket_name}'..."
    )
    # Upload the file
    try:
        logger.debug(f"Opening file '{local_file_path}' for upload.")
        with open(local_file_path, "rb") as f:
            logger.debug(f"Calling put_object for '{object_name}'.")
            response: oci.Response = client.put_object(
                namespace_name=namespace,
                bucket_name=bucket_name,
                object_name=object_name,
                put_object_body=f,
            )
        logger.debug(f"put_object response status: {response.status}")
        if response.status != 200:
            logger.error(
                f"Failed to upload '{local_file_path}' to bucket '{bucket_name}': status={response.status}"
            )
            raise S3UploadError(
                f"Failed to upload '{local_file_path}' to bucket '{bucket_name}': status={response.status}"
            )
        logger.info(f"Successfully uploaded '{local_file_path}' to '{object_name}'.")
    except Exception as e:
        logger.error(
            f"Exception during upload of '{local_file_path}' to bucket '{bucket_name}': {e}"
        )
        raise S3UploadError(
            f"Exception during upload of '{local_file_path}' to bucket '{bucket_name}': {e}"
        )

    if as_zip:
        logger.info(
            f"Skipping presigned URL creation for '{object_name}' as zip is requested."
        )
        return None

    logger.info(f"Creating pre-authenticated request for '{object_name}'...")
    try:
        expiration_time = datetime.utcnow() + timedelta(hours=url_expiration_hours)
        presigned_request_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
            access_type=oci.object_storage.models.CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_READ,
            name=f"presigned-access-{object_name}",
            time_expires=expiration_time,
            object_name=object_name,
        )
        logger.debug(f"Calling create_preauthenticated_request for '{object_name}'.")
        presigned_request_response: oci.Response = (
            client.create_preauthenticated_request(
                namespace_name=namespace,
                bucket_name=bucket_name,
                create_preauthenticated_request_details=presigned_request_details,
            )
        )
        logger.debug(
            f"create_preauthenticated_request response status: {presigned_request_response.status}"
        )
        if presigned_request_response.status not in (200, 201):
            logger.error(
                f"Failed to create pre-authenticated request for '{object_name}': status={presigned_request_response.status}"
            )
            raise S3PresignedUrlError(
                f"Failed to create pre-authenticated request for '{object_name}': status={presigned_request_response.status}"
            )
        presigned_request: oci.object_storage.models.PreauthenticatedRequest = (
            presigned_request_response.data
        )
        logger.info(f"Created pre-authenticated request for '{object_name}'.")
    except Exception as e:
        logger.error(
            f"Exception during pre-authenticated request creation for '{object_name}': {e}"
        )
        raise S3PresignedUrlError(
            f"Exception during pre-authenticated request creation for '{object_name}': {e}"
        )

    logger.info(
        f"Generated presigned URL for '{object_name}': {presigned_request.full_path}"
    )
    return presigned_request.full_path


def upload_and_get_presigned_urls(
    directory_path: Path,
    namespace: str = NAMESPACE_NAME,
    bucket_name: str = BUCKET_NAME,
    url_expiration_hours: int = 1,
    max_workers: int = 5,
    as_zip: bool = False,
) -> list[str]:
    """
    Uploads all files from a local directory to an OCI Object Storage bucket
    and generates a presigned URL for each of them in parallel.

    Args:
        namespace (str): The object storage namespace.
        bucket_name (str): The name of the bucket.
        directory_path (Path): The local path to the directory containing the files.
        url_expiration_hours (int): The number of hours for the presigned URL to be valid.
        max_workers (int): The number of worker threads to use for parallel uploads.

    Returns:
        list[str]: A list of presigned URLs for the uploaded files. Returns
                   an empty list if an error occurs.
    """
    presigned_urls = []

    try:
        logger.info(f"Listing files in directory '{directory_path}' for upload.")
        file_paths_to_upload = [
            file_path for file_path in directory_path.iterdir() if file_path.is_file()
        ]

        if not file_paths_to_upload:
            logger.info("The specified directory is empty. No files to upload.")
            raise S3UploadError(
                f"The specified directory '{directory_path}' is empty. No files to upload."
            )

        # Use the directory's name as the upload folder in the bucket
        upload_folder = directory_path.name
        logger.info(
            f"Uploading {len(file_paths_to_upload)} files to bucket '{bucket_name}' in folder '{upload_folder}'..."
        )
        logger.info(f"Using a thread pool with {max_workers} workers.")

        # Use ThreadPoolExecutor to perform uploads and URL generation in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            tasks = []
            for file_path in file_paths_to_upload:
                object_name = f"{upload_folder}/{file_path.name}"
                logger.info(
                    f"Scheduling upload and presigned URL generation for '{file_path}'."
                )
                tasks.append(
                    executor.submit(
                        _upload_and_create_presigned_url,
                        object_storage_client,
                        namespace,
                        bucket_name,
                        str(file_path),
                        object_name,
                        url_expiration_hours,
                        as_zip,
                    )
                )

            # Collect results as they complete
            for future in concurrent.futures.as_completed(tasks):
                try:
                    url = future.result()
                    presigned_urls.append(url)
                    logger.info(
                        f" - Successfully processed one file. Total URLs: {len(presigned_urls)}"
                    )
                except (S3UploadError, S3PresignedUrlError) as exc:
                    logger.error(f"A file generation task failed: {exc}")
                    raise
                except Exception as exc:
                    logger.error(f"Unexpected error in file generation task: {exc}")
                    raise S3UploadError(
                        f"Unexpected error in file generation task: {exc}"
                    )

        return presigned_urls

    except oci.exceptions.ServiceError as e:
        logger.error(f"OCI ServiceError: {e.code} - {e.message}")
        logger.error("Please check your OCI configuration and permissions.")
        raise S3UploadError(f"OCI ServiceError: {e.code} - {e.message}")
    except FileNotFoundError:
        logger.error(f"Error: The directory '{directory_path}' was not found.")
        raise S3UploadError(f"Error: The directory '{directory_path}' was not found.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise S3UploadError(f"An unexpected error occurred: {e}")


def list_directories(directory: str | None):
    try:
        logger.info(
            f"Listing directories or objects in bucket '{BUCKET_NAME}' for directory: {directory}"
        )

        if directory:
            # List objects inside the specified directory
            prefix = f"{directory}/"
            response = object_storage_client.list_objects(
                namespace_name=NAMESPACE_NAME,
                bucket_name=BUCKET_NAME,
                prefix=prefix,
                fields="name",
            )
            objects = [obj.name for obj in response.data.objects]
            logger.info(f"Found {len(objects)} objects in directory '{directory}'.")
            return {"directory": directory, "objects": objects}
        else:
            # List all directories (prefixes)
            response: oci.Response = object_storage_client.list_objects(
                namespace_name=NAMESPACE_NAME,
                bucket_name=BUCKET_NAME,
                fields="name",
            )
            response_data: oci.object_storage.models.ListObjects = response.data
            objects: list[oci.object_storage.models.ObjectSummary] = (
                response_data.objects
            )
            directories = set(
                obj.name.split("/")[0] for obj in objects if "/" in obj.name
            )
            logger.info(
                f"Found {len(directories)} directories in bucket '{BUCKET_NAME}'."
            )
            return {"directories": list(directories)}
    except oci.exceptions.ServiceError as e:
        logger.error(f"OCI ServiceError: {e.code} - {e.message}")
        raise HTTPException(
            status_code=500, detail=f"OCI ServiceError: {e.code} - {e.message}"
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


# def get_zip_from_presigned_urls(presigned_urls: list[str], download_path: Path) -> Path:
#     """
#     Downloads files from the provided presigned URLs and creates a ZIP archive.

#     Args:
#         presigned_urls (list[str]): List of presigned URLs to download files from.
#         download_path (Path): The local path where the ZIP file will be saved.

#     Returns:
#     """
#     object_storage_client.d
