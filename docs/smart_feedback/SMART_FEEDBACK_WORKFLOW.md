# Smart Feedback System - Workflow Diagram

## 📋 Complete User Journey

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER SUBMITS QUERY                                │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SYSTEM PROCESSES QUERY                                  │
│                   (Analysis & Results Generated)                           │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   SMART FEEDBACK EVALUATION                                │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │   CONFIDENCE    │  │    NOVELTY      │  │    RECENCY      │            │
│  │   SCORING       │  │   DETECTION     │  │   CHECKING      │            │
│  │   (25% weight)  │  │   (30% weight)  │  │   (25% weight)  │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                                 │
│  │ LEARNING VALUE  │  │ FATIGUE         │                                 │
│  │ ASSESSMENT      │  │ DETECTION       │                                 │
│  │ (20% weight)    │  │ (Override)      │                                 │
│  └─────────────────┘  └─────────────────┘                                 │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PRIORITY CALCULATION                                  │
│                                                                             │
│  Weighted Score = (Confidence × 0.25) + (Novelty × 0.30) +               │
│                   (Recency × 0.25) + (Learning Value × 0.20)              │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   DECISION  │
                    └─────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Score ≥ 75% │  │ Score ≥ 55% │  │ Score ≥ 35% │
│    HIGH     │  │   MEDIUM    │  │     LOW     │
│ PRIORITY 🎯 │  │ PRIORITY 💭 │  │ PRIORITY 👍 │
└─────┬───────┘  └─────┬───────┘  └─────┬───────┘
      │                │                │
      ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Orange Border│  │ Blue Border │  │Gray Dashed  │
│"Especially  │  │"Was this    │  │"Quick rating│
│ valuable"   │  │ helpful?"   │  │appreciated" │
│+ Analytics  │  │+ Analytics  │  │             │
└─────┬───────┘  └─────┬───────┘  └─────┬───────┘
      │                │                │
      └────────────────┼────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ USER INTERACTION│
              └─────┬───────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ 👍 YES  │ │ 👎 NO   │ │  SKIP   │
   └────┬────┘ └────┬────┘ └─────────┘
        │           │
        ▼           ▼
   ┌─────────┐ ┌─────────────────────────────────┐
   │ THANK   │ │     CORRECTION INTERFACE        │
   │ YOU     │ │                                 │
   │ MESSAGE │ │ "Help us improve! 🎯"           │
   └─────────┘ │ [Text area for corrections]     │
               │ [Submit Correction] [Skip]      │
               └─────┬───────────────────────────┘
                     │
                     ▼
               ┌─────────────────────────────────┐
               │      AI ANALYSIS & SUGGESTIONS │
               │                                 │
               │ 🟢 High confidence suggestions  │
               │ 🟡 Medium confidence suggestions│
               │ 🔴 Lower confidence suggestions │
               └─────┬───────────────────────────┘
                     │
                     ▼
               ┌─────────────────────────────────┐
               │     LEARNING & IMPROVEMENT      │
               │                                 │
               │ • Pattern recognition           │
               │ • Confidence calibration        │
               │ • Query understanding           │
               │ • Result accuracy               │
               └─────────────────────────────────┘
```

## 🔄 Fatigue Detection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FATIGUE DETECTION                                   │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   CHECK     │
                    │  FREQUENCY  │
                    └─────┬───────┘
                          │
                          ▼
                ┌─────────────────┐
                │ >5 requests in  │ ──YES──┐
                │ last hour?      │        │
                └─────┬───────────┘        │
                      │ NO                 │
                      ▼                    │
                ┌─────────────────┐        │
                │ >70% negative   │ ──YES──┤
                │ in 24 hours?    │        │
                └─────┬───────────┘        │
                      │ NO                 │
                      ▼                    ▼
                ┌─────────────────┐  ┌─────────────────┐
                │ PROCEED WITH    │  │ SKIP FEEDBACK   │
                │ NORMAL PRIORITY │  │ REQUEST         │
                │ CALCULATION     │  │ (FATIGUE        │
                └─────────────────┘  │ DETECTED)       │
                                     └─────────────────┘
```

## 📊 Analytics Tracking Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANALYTICS TRACKING                                 │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   RECORD    │
                    │  REQUEST    │
                    └─────┬───────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATABASE STORAGE                                        │
│                                                                             │
│ • Query text                    • Priority level                           │
│ • User ID                       • Confidence score                         │
│ • Timestamp                     • Novelty score                            │
│ • Requested (Y/N)               • Learning value score                     │
│ • Response received             • Fatigue detected (Y/N)                   │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │  GENERATE   │
                    │  METRICS    │
                    └─────┬───────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      REAL-TIME ANALYTICS                                   │
│                                                                             │
│ • Request Rate: Requests / Total Queries                                   │
│ • Response Rate: Responses / Requests                                      │
│ • Priority Distribution: High/Medium/Low breakdown                         │
│ • User Engagement: Avg requests per user                                   │
│ • Fatigue Rate: Fatigue events / Total users                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Priority Scoring Example

```
Example Query: "What is the correlation between BMI and blood pressure trends?"

┌─────────────────────────────────────────────────────────────────────────────┐
│                        FACTOR CALCULATION                                  │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────┐
│ CONFIDENCE SCORE: 0.4 (Medium confidence)                                  │
│ • Complex statistical query                                                │
│ • Multiple variables involved                                              │
│ • Inverted for priority: 1.0 - 0.4 = 0.6                                 │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────┐
│ NOVELTY SCORE: 0.8 (High novelty)                                         │
│ • "correlation" + "trends" pattern                                        │
│ • Uncommon query type                                                      │
│ • Used directly: 0.8                                                      │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────┐
│ RECENCY SCORE: 0.2 (Low recency)                                          │
│ • No similar queries in last 7 days                                       │
│ • Inverted for priority: 1.0 - 0.2 = 0.8                                 │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────┐
│ LEARNING VALUE: 0.6 (Medium-high learning value)                          │
│ • Complex query structure                                                  │
│ • Multiple field analysis                                                  │
│ • Used directly: 0.6                                                      │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────┐
│                    WEIGHTED CALCULATION                                    │
│                                                                             │
│ Score = (0.6 × 0.25) + (0.8 × 0.30) + (0.8 × 0.25) + (0.6 × 0.20)        │
│       = 0.15 + 0.24 + 0.20 + 0.12                                         │
│       = 0.71                                                               │
│                                                                             │
│ Result: 0.71 ≥ 0.55 → MEDIUM PRIORITY 💭                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*This workflow represents the complete Smart Feedback System v2.2 process flow* 