import Link from "next/link";
import {
  Mountain,
  TrendingUp,
  Heart,
  Gauge,
  ArrowRight,
  BarChart3,
  Calendar,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const features = [
  {
    icon: Mountain,
    title: "Trail dashboard",
    description:
      "Elevation gain/loss, uphill/downhill pace, time on feet. Only what matters for trail.",
  },
  {
    icon: BarChart3,
    title: "Key metrics",
    description:
      "Training Readiness, HRV, Sleep Score, Body Battery. Manage your fitness at a glance.",
  },
  {
    icon: TrendingUp,
    title: "Trends",
    description:
      "Weekly elevation, VO2max, training load. Track your progress from 4 weeks to 1 year.",
  },
  {
    icon: Calendar,
    title: "Activity calendar",
    description:
      "Monthly view of all your runs. Spot patterns, track consistency, plan your week.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <Mountain className="h-5 w-5 text-primary" />
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
      <section className="px-6 pt-20 pb-28 text-center max-w-4xl mx-auto space-y-8">
        <div className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-1.5 text-sm text-muted-foreground">
          <Gauge className="h-3.5 w-3.5" />
          Garmin dashboard for trail runners
        </div>
        <h1 className="text-5xl sm:text-7xl font-bold tracking-tight leading-[1.1]">
          Trail running essentials,
          <br />
          <span className="bg-gradient-to-r from-[#FF8C00] via-[#FF6B00] to-[#0891B2] bg-clip-text text-transparent">
            nothing more.
          </span>
        </h1>
        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Garmin shows 40+ metrics. You use 5. HillsRun cuts through the noise
          and gives you only what matters for trail running.
        </p>
        <div className="flex gap-3 justify-center pt-2">
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

      {/* Dashboard preview */}
      <section className="px-6 pb-20">
        <div className="max-w-5xl mx-auto">
          <div className="rounded-2xl border border-border bg-card/50 backdrop-blur p-8 sm:p-10">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
              {[
                { label: "D+", value: "1,240 m", icon: Mountain, color: "text-[#FF8C00]" },
                { label: "Distance", value: "42.3 km", icon: TrendingUp, color: "text-[#0891B2]" },
                { label: "Readiness", value: "72", icon: Gauge, color: "text-emerald-500" },
                { label: "Resting HR", value: "48 bpm", icon: Heart, color: "text-red-400" },
              ].map((m) => (
                <div key={m.label} className="space-y-2">
                  <m.icon className={`h-5 w-5 mx-auto ${m.color}`} />
                  <p className="text-3xl sm:text-4xl font-bold">{m.value}</p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">{m.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="px-6 py-20 border-t border-border">
        <div className="max-w-3xl mx-auto text-center space-y-4">
          <h2 className="text-2xl sm:text-4xl font-bold">
            Garmin Connect is too much.
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            40 metrics per activity. Charts nobody reads. Data buried in noise.
            For trail running, you need elevation, pace, HR, and daily readiness.
            That&apos;s it.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-20">
        <div className="max-w-5xl mx-auto space-y-10">
          <h2 className="text-2xl sm:text-4xl font-bold text-center">
            What HillsRun shows you
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map((f) => (
              <Card key={f.title} className="group transition-all duration-200 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5">
                <CardContent className="pt-6 space-y-3">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                    <f.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {f.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 py-20 border-t border-border">
        <div className="max-w-4xl mx-auto space-y-10">
          <h2 className="text-2xl sm:text-4xl font-bold text-center">
            Three steps to clarity
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            {[
              { step: "1", icon: Zap, title: "Connect", desc: "Link your Garmin account in one click" },
              { step: "2", icon: TrendingUp, title: "Sync", desc: "Your data flows in automatically" },
              { step: "3", icon: Mountain, title: "Focus", desc: "See only the metrics that matter" },
            ].map((s) => (
              <div key={s.step} className="text-center space-y-3">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                  <span className="text-lg font-bold text-primary">{s.step}</span>
                </div>
                <h3 className="font-semibold text-lg">{s.title}</h3>
                <p className="text-sm text-muted-foreground">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-24">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <h2 className="text-3xl sm:text-4xl font-bold">
            Ready to simplify your trail tracking?
          </h2>
          <p className="text-lg text-muted-foreground">
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
            <Mountain className="h-4 w-4 text-primary" />
            <span className="font-medium">HillsRun</span>
          </div>
          <p>&copy; {new Date().getFullYear()} HillsRun. Built for trail runners.</p>
        </div>
      </footer>
    </div>
  );
}
