import oci
import concurrent.futures
from fastapi import HTTPException
from pathlib import Path
from app.logger import logger
from app.config import settings
from typing import Dict, Tuple


# --- Custom Exceptions ---
class S3UploadError(Exception):
    pass


NAMESPACE_NAME = settings.storage_namespace
BUCKET_NAME = settings.storage_bucket_name
CONFIG_FILE_PATH = Path(settings.oci_config_path)

config = oci.config.from_file(file_location=CONFIG_FILE_PATH)
object_storage_client = oci.object_storage.ObjectStorageClient(config)


def _upload_and_get_public_url(
    client: oci.object_storage.ObjectStorageClient,
    namespace: str,
    bucket_name: str,
    local_file_path: str,
    object_name: str,
) -> Tuple[str, str]:
    """
    Helper function to upload a single file and construct its public URL.
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

    logger.info(f"Constructing public URL for '{object_name}'...")
    try:
        region = client.base_client.config["region"]
        public_url = f"https://{namespace}.objectstorage.{region}.oraclecloud.com/n/{namespace}/b/{bucket_name}/o/{object_name}"

        logger.info(f"Constructed public URL for '{object_name}': {public_url}")

        file_name = Path(local_file_path).name
        return file_name, public_url

    except Exception as e:
        logger.error(
            f"Exception during public URL construction for '{object_name}': {e}"
        )
        raise S3UploadError(
            f"Exception during public URL construction for '{object_name}': {e}"
        )


def upload_and_get_presigned_urls(
    file_paths: list[Path],
    upload_folder: str,
    namespace: str = NAMESPACE_NAME,
    bucket_name: str = BUCKET_NAME,
    max_workers: int = 5,
) -> Dict[str, str]:
    """
    Uploads specific files to an OCI Object Storage bucket
    and generates a public URL for each of them in parallel.

    Args:
        file_paths (list[Path]): List of local paths to the files to upload.
        upload_folder (str): The folder name in the bucket where files will be stored.
        namespace (str): The object storage namespace.
        bucket_name (str): The name of the bucket.
        max_workers (int): The number of worker threads to use for parallel uploads.

    Returns:
        Dict[str, str]: A dictionary of file names and their public URLs for the uploaded files.
                        Returns an empty dict if an error occurs.
    """
    public_urls = {}

    try:
        if not file_paths:
            logger.info("No files provided for upload.")
            return {}

        logger.info(
            f"Uploading {len(file_paths)} files to bucket '{bucket_name}' in folder '{upload_folder}'..."
        )
        logger.info(f"Using a thread pool with {max_workers} workers.")

        # Use ThreadPoolExecutor to perform uploads and URL generation in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            tasks = []
            for file_path in file_paths:
                object_name = f"{upload_folder}/{file_path.name}"
                logger.info(
                    f"Scheduling upload and public URL generation for '{file_path}'."
                )
                tasks.append(
                    executor.submit(
                        _upload_and_get_public_url,
                        object_storage_client,
                        namespace,
                        bucket_name,
                        str(file_path),
                        object_name,
                    )
                )

            # Collect results as they complete
            for future in concurrent.futures.as_completed(tasks):
                try:
                    result = future.result()
                    if result:
                        file_name, url = result
                        public_urls[file_name] = url
                    logger.info(
                        f" - Successfully processed one file. Total URLs: {len(public_urls)}"
                    )
                except S3UploadError as exc:
                    logger.error(f"A file generation task failed: {exc}")
                    raise
                except Exception as exc:
                    logger.error(f"Unexpected error in file generation task: {exc}")
                    raise S3UploadError(
                        f"Unexpected error in file generation task: {exc}"
                    )

        return public_urls

    except oci.exceptions.ServiceError as e:
        logger.error(f"OCI ServiceError: {e.code} - {e.message}")
        logger.error("Please check your OCI configuration and permissions.")
        raise S3UploadError(f"OCI ServiceError: {e.code} - {e.message}")
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
