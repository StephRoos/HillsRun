import Link from "next/link";
import {
  Mountain,
  TrendingUp,
  Heart,
  Gauge,
  ArrowRight,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const features = [
  {
    icon: Mountain,
    title: "Dashboard trail",
    description:
      "Elevation gain/loss, uphill/downhill pace, time on feet. Only what matters for trail.",
  },
  {
    icon: BarChart3,
    title: "Key metrics",
    description:
      "Training Readiness, HRV, Sleep Score, Body Battery. Just what you need to manage your fitness.",
  },
  {
    icon: TrendingUp,
    title: "Trends",
    description:
      "Weekly elevation, VO2max, training load. Track your progress from 4 weeks to 1 year.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <Mountain className="h-5 w-5 text-emerald-500" />
          <span className="text-lg font-bold">HillsRun</span>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/login">Sign in</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/signup">Sign up</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="px-6 py-24 text-center max-w-4xl mx-auto space-y-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-1.5 text-sm text-muted-foreground">
          <Gauge className="h-3.5 w-3.5" />
          Garmin dashboard for trail runners
        </div>
        <h1 className="text-4xl sm:text-6xl font-bold tracking-tight">
          Trail running essentials,
          <br />
          <span className="text-emerald-500">for you and your crew.</span>
        </h1>
        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto">
          Garmin shows 40+ metrics. You use 5. HillsRun shows you only what matters for trail running.
        </p>
        <div className="flex gap-3 justify-center pt-4">
          <Button size="lg" asChild>
            <Link href="/signup">
              Get started free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </section>

      {/* Problem */}
      <section className="px-6 py-16 border-t border-border">
        <div className="max-w-4xl mx-auto text-center space-y-4">
          <h2 className="text-2xl sm:text-3xl font-bold">
            Garmin Connect is too much.
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            40 metrics per activity. Charts nobody reads. Data buried in noise. For trail running, you need elevation gain, pace, HR and daily readiness. That&apos;s it.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-16">
        <div className="max-w-5xl mx-auto space-y-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-center">
            What HillsRun shows you
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {features.map((f) => (
              <Card key={f.title}>
                <CardContent className="pt-6 space-y-3">
                  <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                    <f.icon className="h-5 w-5 text-emerald-500" />
                  </div>
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {f.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Dashboard preview */}
      <section className="px-6 py-16 border-t border-border">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <h2 className="text-2xl sm:text-3xl font-bold">
            A dashboard that cuts to the chase
          </h2>
          <div className="rounded-xl border border-border bg-card p-6 sm:p-8">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              {[
                { label: "D+", value: "1 240 m", icon: Mountain },
                { label: "Distance", value: "42.3 km", icon: TrendingUp },
                { label: "Readiness", value: "72", icon: Gauge },
                { label: "Resting HR", value: "48 bpm", icon: Heart },
              ].map((m) => (
                <div key={m.label} className="space-y-1">
                  <m.icon className="h-5 w-5 mx-auto text-emerald-500" />
                  <p className="text-2xl font-bold">{m.value}</p>
                  <p className="text-xs text-muted-foreground">{m.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <h2 className="text-2xl sm:text-3xl font-bold">
            Ready to simplify your trail tracking?
          </h2>
          <p className="text-muted-foreground">
            Free. Connect your Garmin watch and start now.
          </p>
          <Button size="lg" asChild>
            <Link href="/signup">
              Create my account
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Mountain className="h-4 w-4 text-emerald-500" />
            <span>HillsRun</span>
          </div>
          <p>&copy; {new Date().getFullYear()} HillsRun. Built for trail runners.</p>
        </div>
      </footer>
    </div>
  );
}
