# Product Requirements Document: HillsRun

## Product Vision

**Problem Statement**
Trail runners and endurance athletes find Garmin Connect overwhelming with excessive noise (ads, promotional content, feature overload). They need a focused, distraction-free dashboard that showcases essential trail metrics (elevation gain, VO2max, HRV, training readiness) and supports coaching workflows where coaches monitor multiple athletes.

**Solution**
HillsRun is a trail-focused Garmin dashboard built as an antidote to Garmin Connect noise. It syncs live data from Garmin Connect (activities, daily health, body composition, advanced metrics, wellness) and surfaces the metrics that matter to serious trail athletes. Multi-user coaching support allows coaches to invite athletes and view their data via invite codes. Eventually integrable with RecettesApp for a unified training + nutrition ecosystem.

**Success Criteria**
- Athletes use HillsRun as their primary Garmin data dashboard within 2 weeks
- 90%+ of activities auto-sync without manual intervention
- Coaches can manage 5+ athletes with sub-30-second athlete switching
- User retention > 70% at 30 days

## Target Users

### Primary Persona: Jordan — The Trail Runner
- **Role**: Endurance/trail runner training 3–5 times per week
- **Pain Points**:
  - Garmin Connect is cluttered with unnecessary promotions and features
  - Wants to focus on elevation, pace, heart rate variability, training load
  - Manually opens Garmin Connect multiple times daily to check readiness
  - No place to see planned workouts alongside actual performance
- **Motivations**: Optimize training through cleaner data visualization
- **Goals**: See today's readiness score and weekly training load in < 5 seconds; plan workouts for the week

### Secondary Persona: Coach — Multi-Athlete Manager
- **Role**: Running coach responsible for 5–20 athletes
- **Pain Points**:
  - Must log into each athlete's Garmin account separately to check progress
  - No simple way to invite athletes or request access
  - Cannot see all athletes' data in one place
- **Motivations**: Deliver better coaching by monitoring athlete recovery and load
- **Goals**: Invite an athlete via code; see their activity feed and training readiness; switch between athletes in < 3 seconds

### Tertiary Persona: Future User — Nutrition-Focused Athlete
- **Role**: Trail runner who also uses RecettesApp
- **Pain Points**: Training and nutrition are siloed in separate apps
- **Motivations**: See training volume + nutrition in one ecosystem
- **Goals**: See recommended caloric intake based on training load; sync meal plans with training calendar

## Core Features (MVP)

### Must-Have Features

#### 1. Garmin Data Sync & Auto-Sync
**Description**: Automatic + manual sync of Garmin Connect data (activities, daily health metrics, body composition, HRV, VO2max, training load, wellness, sleep). Incremental sync on login + full sync option. Job tracking UI shows last sync time, next scheduled sync, sync status. MFA support for secure Garmin credential storage.
**User Value**: Always up-to-date data without manual exports; coaches can see fresh athlete data.
**Success Metric**: 90%+ auto-sync success rate; manual sync completion time < 10 seconds.

#### 2. Dashboard with Training Readiness
**Description**: At-a-glance weekly summary: weekly volume (km), elevation gain (m), VO2max trend, training load gauge, daily activity count. Large Training Readiness gauge (0–100, color-coded red/yellow/green). Today's activities mini-feed. Activity calendar heatmap (weeks 1–4, color by volume or load).
**User Value**: Understand training status and readiness in under 5 seconds; plan the day with confidence.
**Success Metric**: Dashboard load time < 2 seconds; 95%+ of users visit daily.

#### 3. Activity Detail Page
**Description**: Full activity breakdown: title, distance, duration, pace, elevation, HR avg/max, VMA (velocity at VO2max), HR zones, cadence. Interactive splits charts (elevation, pace, HR over time). Splits table. Similar activities comparison. Edit activity name and notes.
**User Value**: Deep dive into any run; understand pacing strategy and physiological response.
**Success Metric**: 40%+ of weekly activities viewed in detail.

#### 4. Monthly Calendar & Planned Workouts
**Description**: TrainingPeaks-style monthly view. Cells show actual activities + planned workouts (color-coded by type: easy, tempo, long run, strength). CRUD planned workouts (title, date, type, distance, notes). CSV bulk import of planned workouts. Template download for future planning sessions. Drag-to-reschedule or click-to-edit.
**User Value**: Train to a plan; see actual vs planned performance; import from external plans (e.g., Strava, TrainingPeaks).
**Success Metric**: > 80% of athletes plan weekly workouts; CSV import used 1x per month.

#### 5. Trends Dashboard with 8 Charts
**Description**: Plotly-based interactive charts:
  - Weekly volume (km)
  - Weekly elevation gain (m)
  - VO2max trend (rolling 30d avg)
  - Heart rate variability (HRV) over time
  - Training load (TSS or Garmin Training Load) by week
  - Sleep duration & quality (weekly avg)
  - Body weight / composition over time
  - Stress levels (if available from Garmin wellness)
Period selector: 4 weeks, 3 months, 6 months, 1 year. Hover for details. Period-over-period comparison if data available.
**User Value**: Spot trends, see if training is sustainable, detect overtraining or detraining.
**Success Metric**: Trends page visited 2x per week; trend view triggers workout plan adjustments 30%+ of weeks.

#### 6. Settings & Profile Management
**Description**: User profile (name, email, preferred distance unit: km/mi). Garmin Connect credential management: link/unlink Garmin account (with MFA support). Coaching settings: manage athletes (for coaches), join as athlete (via invite code). Webhook or scheduler logs for sync troubleshooting.
**User Value**: Secure credential storage; simple invite-based coaching access; transparency into sync health.
**Success Metric**: 95%+ successful Garmin account links; coaching invites issued < 30 seconds.

#### 7. Coaching: Invite-Based Multi-Athlete Access
**Description**: Coach generates invite code (random, 8 alphanumeric, 7-day expiry). Athlete receives code (via email/manual), enters code in settings. Coach sees athlete in sidebar under "My Athletes". Dropdown to switch between athletes instantly. Coach can view athlete's dashboard, activities, calendar, trends (read-only or restricted edit based on permission level). Each athlete revokes coach access independently.
**User Value**: Coaches manage multiple athletes without security overhead; athletes control who sees what.
**Success Metric**: Invite code generation < 2 seconds; coach athlete-switch < 1 second; < 5% coach revocation rate per month.

#### 8. Responsive & Offline-Ready (PWA)
**Description**: Mobile-first responsive design (Tailwind). Serwist-based offline caching: cached dashboard, activity list, trends work offline. Real-time badge shows online/offline status. Sync queued when offline, executed on reconnect.
**User Value**: View historical data on flights, trail runs in remote areas; no dropped data.
**Success Metric**: Offline dashboard load time < 500ms from cache; 0% data loss on offline→online reconnect.

### Should-Have Features (Post-MVP)

- **RecettesApp Integration**: Sync caloric objective from HillsRun training load; suggest daily calorie targets to RecettesApp
- **Fix Scheduler DB Constraints**: Re-enable periodic background sync (currently manual/login-trigger only)
- **Activity Recommendations**: "Based on your current VO2max and TSS, here are ideal workouts for the week"
- **Social/Community**: Public athlete profiles, shared route library, community challenges
- **Garmin Smart Notification Badges**: Desktop notifications for readiness score changes
- **Export Options**: PDF of weekly summary, GPX of activities for external use
- **Third-Party OAuth**: Direct Garmin OAuth (currently uses username/password in Garmin's auth flow)

## User Flows

### Primary Flow: Athlete Checks Readiness & Plans Day
1. Athlete opens HillsRun dashboard
2. Training Readiness gauge is prominently displayed (e.g., "73/100 — Go easy today")
3. Today's activities mini-feed shows any pre-planned workouts or auto-detected activities
4. Athlete opens Calendar to see the week's plan
5. If no plan exists, athlete can add a workout manually or import a template
6. Athlete reviews Trends to check VO2max and HRV
7. If readiness is low, athlete adjusts planned workout intensity or swaps to an easy day

### Secondary Flow: Coach Invites Athlete & Monitors
1. Coach opens Settings → Coaching
2. Coach clicks "Generate Athlete Invite Code"
3. Code is generated (e.g., `ABC123DE`); coach sends via email or SMS
4. Athlete receives code, opens Settings → Coaching, enters code
5. Coach refreshes sidebar; athlete now appears in "My Athletes"
6. Coach clicks athlete name to switch context
7. Coach sees athlete's dashboard, calendar, trends, activities (read-only)
8. Coach reviews athlete's VO2max trend and comments on activities to adjust plan
9. Athlete can revoke coach access anytime via Settings

### Tertiary Flow: Planned Workout via CSV Import
1. Athlete exports training plan from TrainingPeaks / Strava (CSV format)
2. Athlete opens Calendar → "Import Plan"
3. Athlete selects CSV file
4. HillsRun parses and previews planned workouts
5. Athlete confirms; workouts are inserted into calendar
6. Planned vs. actual comparison begins as athlete executes workouts

## Out of Scope (v1)

Explicitly NOT included in the initial release:
- **No RecettesApp Integration**: Designed to integrate post-MVP; feature flag available for future hookup
- **No Direct Garmin OAuth**: Currently uses Garmin's user/password flow; OAuth requires Garmin API approval
- **No Native Mobile App**: Responsive web only; PWA replaces native for offline support
- **No Community/Social Features**: Public profiles, shared routes, challenges deferred post-MVP
- **No Real-Time Notifications**: Sync is periodic + login-triggered, not push-based
- **No Video or AI Coach**: No AI-driven workout recommendations or technique analysis in v1
- **No Multi-Language**: English only in v1; i18n framework in place for future

## Open Questions

- Should periodic background sync be re-enabled (requires scheduler DB constraints fix)?
- What is the desired permission model for coaches (read-only vs. edit notes)?
- Which metrics take priority on mobile: readiness, VO2max, or training load?
- Should Garmin credentials be re-encrypted if stored locally, or always proxied through backend?

## Success Metrics

**Primary Metrics**:
- **Adoption**: 50+ athletes using within first month
- **Daily Active Users (DAU)**: 70%+ of athletes visit dashboard daily
- **Auto-Sync Success**: 90%+ of syncs complete without error
- **Retention**: > 70% at 30 days

**Secondary Metrics**:
- **Calendar Planning**: > 80% of athletes plan at least 1 week of workouts
- **Coaching**: > 30% of coaches manage 3+ athletes with < 5% revocation rate
- **Engagement**: Trends page visited 2x per week by 60%+ of athletes
- **Performance**: Dashboard load time < 2 seconds (p95); activity detail < 1 second

## Timeline & Milestones

- **Phase 1 (Weeks 1–2)**: Backend Garmin sync + database schema finalization, frontend auth integration
- **Phase 2 (Weeks 3–4)**: Dashboard + activity detail + calendar (no planning yet)
- **Phase 3 (Weeks 5–6)**: Planned workouts CRUD + CSV import, coaching invites
- **Phase 4 (Weeks 7–8)**: Trends dashboard (8 charts) + settings refinement
- **Phase 5 (Weeks 9–10)**: PWA + offline caching, performance optimization, polishing UI
- **Phase 6 (Weeks 11–12)**: Bug fixes, load testing, documentation, deployment readiness
- **MVP Launch**: ~12 weeks; phased beta with 20–50 athletes
- **Post-MVP**: RecettesApp integration, scheduler re-enabling, community features

## Technical Stack

- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui, Plotly.js (Trends), Serwist (PWA)
- **Backend**: FastAPI (Python), async request handling, background job queue (Celery or APScheduler)
- **Database**: PostgreSQL 15+, 15+ Garmin data tables (Activities, DailyMetrics, HRV, VO2max, Stress, Sleep, etc.)
- **Auth**: Better-Auth (email/password), secure Garmin credential storage (encrypted)
- **Deployment**:
  - Backend: UGREEN NAS (ARM64), Docker, Cloudflare Tunnel
  - Frontend: Vercel (automatic deployment on push)
- **Monitoring**: Basic health checks; job logs in database
- **Future**: Possible RecettesApp API integration via shared backend scheme

## Architecture Notes

- Incremental Garmin sync minimizes API calls; full sync available on demand
- Coaching invite codes are short-lived (7-day expiry) for security
- Trends data is aggregated weekly (not real-time) to reduce DB queries
- Offline caching uses Serwist with a stale-while-revalidate strategy
- All athlete data is private until coach is explicitly invited
