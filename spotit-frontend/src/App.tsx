import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { URLInputForm } from "@/components/URLInputForm";
import { AudioPlayer } from "@/components/AudioPlayer";
import { useMutation } from "@tanstack/react-query";
import * as z from "zod";

const queryClient = new QueryClient();

const FormSchema = z.object({
  url: z.string().url(),
});

import { useEffect } from "react";
import { generateStems, triggerColdBoot } from "@/api";

// ...

function App() {
  useEffect(() => {
    triggerColdBoot();
  }, []);

  const { mutate, isPending, data, error } = useMutation({
    mutationFn: (data: z.infer<typeof FormSchema>) => generateStems(data.url),
  });

  const onSubmit = (data: z.infer<typeof FormSchema>) => {
    mutate(data);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary font-sans antialiased">
      <div className="container relative flex min-h-screen flex-col items-center justify-center">
        <div className="flex w-full max-w-md flex-col items-center space-y-8 rounded-lg bg-card p-8 shadow-lg">
          <h1 className="text-5xl font-bold tracking-tighter text-primary">SpotIt</h1>
          <p className="text-muted-foreground">
            Separate audio tracks from your favorite songs.
          </p>
          <URLInputForm onSubmit={onSubmit} isLoading={isPending} />
          {isPending && <p>Loading...</p>}
          {error && <p className="text-red-500">{error.message}</p>}
          {data && <AudioPlayer urls={data.urls} />}
        </div>
      </div>
    </div>
  );
}

export default function WrappedApp() {
  return (
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );
}