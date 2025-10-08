import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

const FormSchema = z.object({
  url: z.string().url({
    message: "Please enter a valid URL.",
  }),
});

export function URLInputForm({
  onSubmit,
  isLoading,
}: {
  onSubmit: (data: z.infer<typeof FormSchema>) => void;
  isLoading: boolean;
}) {
  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      url: "",
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="w-2/3 space-y-6">
        <FormField
          control={form.control}
          name="url"
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Input placeholder="YouTube or Spotify URL" {...field} className="" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-center">
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Generating..." : "Generate"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
