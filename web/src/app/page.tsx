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
      "D+, D-, allure montée/descente, temps sur les pieds. Uniquement ce qui compte pour le trail.",
  },
  {
    icon: BarChart3,
    title: "Métriques essentielles",
    description:
      "Training Readiness, HRV, Sleep Score, Body Battery. Le strict nécessaire pour piloter ta forme.",
  },
  {
    icon: TrendingUp,
    title: "Tendances",
    description:
      "D+ hebdo, VO2max, charge d'entraînement. Visualise ta progression sur 4 semaines à 1 an.",
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
            <Link href="/login">Se connecter</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/signup">S&apos;inscrire</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="px-6 py-24 text-center max-w-4xl mx-auto space-y-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-1.5 text-sm text-muted-foreground">
          <Gauge className="h-3.5 w-3.5" />
          Dashboard Garmin pour traileurs
        </div>
        <h1 className="text-4xl sm:text-6xl font-bold tracking-tight">
          L&apos;essentiel du trail,
          <br />
          <span className="text-emerald-500">pour toi et ton crew.</span>
        </h1>
        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto">
          Garmin affiche 40+ métriques. Tu en utilises 5. HillsRun te montre
          uniquement ce qui compte pour le trail.
        </p>
        <div className="flex gap-3 justify-center pt-4">
          <Button size="lg" asChild>
            <Link href="/signup">
              Commence gratuitement
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/login">Se connecter</Link>
          </Button>
        </div>
      </section>

      {/* Problem */}
      <section className="px-6 py-16 border-t border-border">
        <div className="max-w-4xl mx-auto text-center space-y-4">
          <h2 className="text-2xl sm:text-3xl font-bold">
            Garmin Connect, c&apos;est trop.
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            40 métriques par activité. Des graphiques que personne ne lit. Des
            données noyées dans du bruit. Pour le trail, tu as besoin de D+,
            d&apos;allure, de FC et de ta forme du jour. Point.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-16">
        <div className="max-w-5xl mx-auto space-y-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-center">
            Ce que HillsRun te montre
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
            Un dashboard qui va droit au but
          </h2>
          <div className="rounded-xl border border-border bg-card p-6 sm:p-8">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              {[
                { label: "D+", value: "1 240 m", icon: Mountain },
                { label: "Distance", value: "42.3 km", icon: TrendingUp },
                { label: "Readiness", value: "72", icon: Gauge },
                { label: "FC repos", value: "48 bpm", icon: Heart },
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
            Prêt à simplifier ton suivi trail ?
          </h2>
          <p className="text-muted-foreground">
            Gratuit. Connecte ta montre Garmin et commence maintenant.
          </p>
          <Button size="lg" asChild>
            <Link href="/signup">
              Créer mon compte
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
          <p>&copy; {new Date().getFullYear()} HillsRun. Fait pour les traileurs.</p>
        </div>
      </footer>
    </div>
  );
}
