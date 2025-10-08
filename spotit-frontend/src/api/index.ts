const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://amitbar2001-spotit.hf.space";

interface GenerateStemsResponse {
    urls: string[];
}

const generateStemsFromSpotify = async (spotifyUrl: string): Promise<GenerateStemsResponse> => {
  const response = await fetch(`${BASE_URL}/separate-from-youtube/?spotify_playlist=${encodeURIComponent(spotifyUrl)}`, {
    method: "POST",
    body: JSON.stringify({ url: spotifyUrl }),
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error("Failed to generate stems from Spotify URL");
  }
    return response.json();
};

const generateStemsFromYoutube = async (youtubeUrl: string): Promise<GenerateStemsResponse> => {
  const response = await fetch(`${BASE_URL}/separate-from-youtube/`, {
    method: "POST",
    body: JSON.stringify({ url: youtubeUrl }),
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error("Failed to generate stems from YouTube URL");
  }
    return response.json();
};

export const generateStems = async (url: string): Promise<GenerateStemsResponse> => {
  let response: GenerateStemsResponse;
  
  if (url.includes("spotify.com")) {
    response = await generateStemsFromSpotify(url);
  } else if (url.includes("youtube.com") || url.includes("youtu.be")) {
    response = await generateStemsFromYoutube(url);
  } else {
    throw new Error("Invalid URL. Please provide a Spotify or YouTube URL.");
  }

  const first = response.urls.find((url) => url.includes("drums.mp3"));
  return {urls: first ? [first, ...response.urls.filter(url => !url.includes("drums.mp3")).sort()] : response.urls.sort()};
};

export const triggerColdBoot = async (): Promise<void> => {
  try {
    // We don't need to do anything with the response, just make the request.
    await fetch(`${BASE_URL}`, { method: "GET" });
    console.log("Cold boot triggered.");
  } catch (error) {
    console.error("Failed to trigger cold boot:", error);
  }
};
