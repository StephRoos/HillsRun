import { Skeleton } from "@/components/ui/skeleton";

export default function AuthLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Skeleton className="h-96 w-full max-w-md rounded-lg" />
    </div>
  );
}
