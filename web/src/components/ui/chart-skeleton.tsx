import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface ChartSkeletonProps {
  variant?: "small" | "medium" | "large";
}

const HEIGHTS: Record<NonNullable<ChartSkeletonProps["variant"]>, string> = {
  small: "h-[180px]",
  medium: "h-[280px]",
  large: "h-[400px]",
};

export function ChartSkeleton({ variant = "medium" }: ChartSkeletonProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className={`w-full ${HEIGHTS[variant]}`} />
      </CardContent>
    </Card>
  );
}
