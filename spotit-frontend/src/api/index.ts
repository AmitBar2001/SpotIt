const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

interface GenerateStemsResponse {
    urls: string[];
}

const generateStemsFromSpotify = async (spotifyUrl: string): Promise<GenerateStemsResponse> => {
  const response = await fetch(`${BASE_URL}/separate-from-spotify`, {
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
  const response = await fetch(`${BASE_URL}/separate-from-youtube`, {
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
  if (url.includes("spotify.com")) {
    return generateStemsFromSpotify(url);
  } else if (url.includes("youtube.com") || url.includes("youtu.be")) {
    return generateStemsFromYoutube(url);
  } else {
    throw new Error("Invalid URL. Please provide a Spotify or YouTube URL.");
  }
};