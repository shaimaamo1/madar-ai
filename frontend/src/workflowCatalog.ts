// Generated from workflows/*.json by scripts/generate_architecture.py.
export const workflowCatalog = [
  {
    "name": "MADAR Delivery Reconciliation",
    "key": "madar-delivery-reconciliation",
    "nodes": [
      {
        "id": "schedule",
        "name": "Review provider outcomes",
        "type": "scheduleTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "escalate-uncertain-and-failed-delivery",
        "name": "Escalate uncertain and failed delivery",
        "type": "httpRequest",
        "position": [
          460,
          220
        ]
      },
      {
        "id": "incidents-need-operator-review",
        "name": "Incidents need operator review",
        "type": "if",
        "position": [
          780,
          220
        ]
      },
      {
        "id": "return-reconciliation-queue",
        "name": "Return reconciliation queue",
        "type": "code",
        "position": [
          1070,
          110
        ]
      },
      {
        "id": "return-clean-delivery-review",
        "name": "Return clean delivery review",
        "type": "code",
        "position": [
          1070,
          330
        ]
      },
      {
        "id": "reliability-and-audit",
        "name": "RELIABILITY AND AUDIT",
        "type": "stickyNote",
        "position": [
          110,
          75
        ],
        "note": "## RELIABILITY AND AUDIT\nRetries: transient provider rejections only, exponential backoff, five attempts. Uncertain network outcomes create one operator incident per message; no blind replay.",
        "width": 900,
        "height": 300
      },
      {
        "id": "operator-escalation",
        "name": "OPERATOR ESCALATION",
        "type": "stickyNote",
        "position": [
          1010,
          35
        ],
        "note": "## OPERATOR ESCALATION\nDashboard-only incident queue. Customer text and provider errors are not copied to workflow logs or external notification accounts.",
        "width": 360,
        "height": 430
      }
    ],
    "edges": [
      {
        "source": "Review provider outcomes",
        "target": "Escalate uncertain and failed delivery",
        "branch": 0
      },
      {
        "source": "Escalate uncertain and failed delivery",
        "target": "Incidents need operator review",
        "branch": 0
      },
      {
        "source": "Incidents need operator review",
        "target": "Return reconciliation queue",
        "branch": 0
      },
      {
        "source": "Incidents need operator review",
        "target": "Return clean delivery review",
        "branch": 1
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/reconcile"
    ]
  },
  {
    "name": "MADAR Error Monitor",
    "key": "madar-error-monitor",
    "nodes": [
      {
        "id": "error",
        "name": "Workflow failure",
        "type": "errorTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "summary",
        "name": "Redacted incident summary",
        "type": "code",
        "position": [
          430,
          220
        ]
      },
      {
        "id": "record-operator-incident",
        "name": "Record operator incident",
        "type": "httpRequest",
        "position": [
          700,
          220
        ]
      },
      {
        "id": "restricted-incident-escalation",
        "name": "RESTRICTED INCIDENT ESCALATION",
        "type": "stickyNote",
        "position": [
          110,
          100
        ],
        "note": "## RESTRICTED INCIDENT ESCALATION\nIdentifiers only. Opens an auditable dashboard incident. No customer payloads, tokens, email or Slack notifications.",
        "width": 850,
        "height": 250
      }
    ],
    "edges": [
      {
        "source": "Workflow failure",
        "target": "Redacted incident summary",
        "branch": 0
      },
      {
        "source": "Redacted incident summary",
        "target": "Record operator incident",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/incidents"
    ]
  },
  {
    "name": "MADAR Follow-up Scheduler",
    "key": "madar-follow-up-scheduler",
    "nodes": [
      {
        "id": "schedule",
        "name": "Every five minutes",
        "type": "scheduleTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "evaluate-due-follow-ups",
        "name": "Evaluate due follow-ups",
        "type": "httpRequest",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "read-delivery-authorization",
        "name": "Read delivery authorization",
        "type": "httpRequest",
        "position": [
          680,
          220
        ]
      },
      {
        "id": "owner-authorized-delivery",
        "name": "Owner authorized delivery",
        "type": "if",
        "position": [
          940,
          220
        ]
      },
      {
        "id": "dispatch-approved-delivery",
        "name": "Dispatch approved delivery",
        "type": "httpRequest",
        "position": [
          1200,
          150
        ]
      },
      {
        "id": "return-queued-sandbox-status",
        "name": "Return queued sandbox status",
        "type": "code",
        "position": [
          1200,
          340
        ]
      },
      {
        "id": "consent-and-re-engagement",
        "name": "CONSENT AND RE-ENGAGEMENT",
        "type": "stickyNote",
        "position": [
          100,
          75
        ],
        "note": "## CONSENT AND RE-ENGAGEMENT\nBackend enforces consent, opt-out, human takeover, due dates, reactivation and per-task idempotency.",
        "width": 790,
        "height": 280
      },
      {
        "id": "approval-boundary",
        "name": "APPROVAL BOUNDARY",
        "type": "stickyNote",
        "position": [
          900,
          75
        ],
        "note": "## APPROVAL BOUNDARY\nProvider dispatch independently re-checks authorization, messaging windows and attempt limits.",
        "width": 520,
        "height": 410
      }
    ],
    "edges": [
      {
        "source": "Every five minutes",
        "target": "Evaluate due follow-ups",
        "branch": 0
      },
      {
        "source": "Evaluate due follow-ups",
        "target": "Read delivery authorization",
        "branch": 0
      },
      {
        "source": "Read delivery authorization",
        "target": "Owner authorized delivery",
        "branch": 0
      },
      {
        "source": "Owner authorized delivery",
        "target": "Dispatch approved delivery",
        "branch": 0
      },
      {
        "source": "Owner authorized delivery",
        "target": "Return queued sandbox status",
        "branch": 1
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/tick",
      "/api/bridge/status",
      "/api/bridge/dispatch"
    ]
  },
  {
    "name": "MADAR Ingestion Subworkflow",
    "key": "madar-ingestion-subworkflow",
    "nodes": [
      {
        "id": "sub",
        "name": "Called by workflow",
        "type": "executeWorkflowTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "validate-normalized-inquiry",
        "name": "Validate normalized inquiry",
        "type": "code",
        "position": [
          400,
          220
        ]
      },
      {
        "id": "normalize-inquiry",
        "name": "Normalize inquiry",
        "type": "httpRequest",
        "position": [
          650,
          220
        ]
      },
      {
        "id": "atomic-crm-transaction",
        "name": "ATOMIC CRM TRANSACTION",
        "type": "stickyNote",
        "position": [
          110,
          100
        ],
        "note": "## ATOMIC CRM TRANSACTION\nReceipt deduplication, contact resolution, qualification, scoring, inventory matching, assignment, history and gated outbox commit together.",
        "width": 810,
        "height": 250
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate normalized inquiry",
        "branch": 0
      },
      {
        "source": "Validate normalized inquiry",
        "target": "Normalize inquiry",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/integrations/ingest"
    ]
  },
  {
    "name": "MADAR Lead Intelligence",
    "key": "madar-lead-intelligence",
    "nodes": [
      {
        "id": "sub",
        "name": "Called by workflow",
        "type": "executeWorkflowTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "validate-customer-reference",
        "name": "Validate customer reference",
        "type": "code",
        "position": [
          400,
          220
        ]
      },
      {
        "id": "read-intent-score-and-inventory",
        "name": "Read intent score and inventory",
        "type": "httpRequest",
        "position": [
          670,
          220
        ]
      },
      {
        "id": "human-adviser-requested",
        "name": "Human adviser requested",
        "type": "if",
        "position": [
          950,
          220
        ]
      },
      {
        "id": "ensure-adviser-escalation-task",
        "name": "Ensure adviser escalation task",
        "type": "httpRequest",
        "position": [
          1230,
          100
        ]
      },
      {
        "id": "return-actionable-recommendations",
        "name": "Return actionable recommendations",
        "type": "code",
        "position": [
          1230,
          340
        ]
      },
      {
        "id": "authoritative-intelligence",
        "name": "AUTHORITATIVE INTELLIGENCE",
        "type": "stickyNote",
        "position": [
          110,
          75
        ],
        "note": "## AUTHORITATIVE INTELLIGENCE\nArabic / English qualification and workload assignment happen atomically at ingestion. This module reads persisted CRM evidence and real available inventory.",
        "width": 810,
        "height": 280
      },
      {
        "id": "human-ownership",
        "name": "HUMAN OWNERSHIP",
        "type": "stickyNote",
        "position": [
          920,
          35
        ],
        "note": "## HUMAN OWNERSHIP\nPersistent handoff pauses automated sales replies. Escalation tasks are deduplicated. Recommendations never fabricate listing facts.",
        "width": 580,
        "height": 440
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate customer reference",
        "branch": 0
      },
      {
        "source": "Validate customer reference",
        "target": "Read intent score and inventory",
        "branch": 0
      },
      {
        "source": "Read intent score and inventory",
        "target": "Human adviser requested",
        "branch": 0
      },
      {
        "source": "Human adviser requested",
        "target": "Ensure adviser escalation task",
        "branch": 0
      },
      {
        "source": "Human adviser requested",
        "target": "Return actionable recommendations",
        "branch": 1
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/intelligence",
      "/api/bridge/handoff"
    ]
  },
  {
    "name": "MADAR Omnichannel Intake",
    "key": "madar-omnichannel-intake",
    "nodes": [
      {
        "id": "intake-webhook",
        "name": "Authenticated normalized events",
        "type": "webhook",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "normalize-trusted-envelope",
        "name": "Normalize trusted envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "crm-intake-transaction",
        "name": "CRM intake transaction",
        "type": "httpRequest",
        "position": [
          680,
          220
        ]
      },
      {
        "id": "new-event-accepted",
        "name": "New event accepted",
        "type": "if",
        "position": [
          930,
          100
        ]
      },
      {
        "id": "resolve-sales-intelligence",
        "name": "Resolve sales intelligence",
        "type": "executeWorkflow",
        "position": [
          950,
          300
        ]
      },
      {
        "id": "acknowledge-accepted-event",
        "name": "Acknowledge accepted event",
        "type": "respondToWebhook",
        "position": [
          1450,
          220
        ]
      },
      {
        "id": "authenticated-intake",
        "name": "AUTHENTICATED INTAKE",
        "type": "stickyNote",
        "position": [
          100,
          0
        ],
        "note": "## AUTHENTICATED INTAKE\nWebsite / CRM / authorized inbox sources send normalized events. Meta signatures terminate at MADAR /webhooks/meta, never at this JSON webhook.",
        "width": 770,
        "height": 440
      },
      {
        "id": "replay-and-context",
        "name": "REPLAY AND CONTEXT",
        "type": "stickyNote",
        "position": [
          890,
          0
        ],
        "note": "## REPLAY AND CONTEXT\nDuplicate events skip intelligence work. Import helper resolves subworkflow IDs. HTTP retries reuse stable event IDs.",
        "width": 780,
        "height": 460
      }
    ],
    "edges": [
      {
        "source": "Authenticated normalized events",
        "target": "Normalize trusted envelope",
        "branch": 0
      },
      {
        "source": "Normalize trusted envelope",
        "target": "CRM intake transaction",
        "branch": 0
      },
      {
        "source": "CRM intake transaction",
        "target": "New event accepted",
        "branch": 0
      },
      {
        "source": "New event accepted",
        "target": "Resolve sales intelligence",
        "branch": 0
      },
      {
        "source": "New event accepted",
        "target": "Acknowledge accepted event",
        "branch": 1
      },
      {
        "source": "Resolve sales intelligence",
        "target": "Acknowledge accepted event",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/integrations/ingest"
    ]
  },
  {
    "name": "MADAR Sales Reporting",
    "key": "madar-sales-reporting",
    "nodes": [
      {
        "id": "schedule",
        "name": "Daily company reporting",
        "type": "scheduleTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "compute-tenant-sales-report",
        "name": "Compute tenant sales report",
        "type": "httpRequest",
        "position": [
          430,
          220
        ]
      },
      {
        "id": "build-executive-report-artifact",
        "name": "Build executive report artifact",
        "type": "code",
        "position": [
          720,
          220
        ]
      },
      {
        "id": "real-crm-measurement",
        "name": "REAL CRM MEASUREMENT",
        "type": "stickyNote",
        "position": [
          110,
          90
        ],
        "note": "## REAL CRM MEASUREMENT\nRecorded sales, earned commissions, sources, response time and team conversion. Returns a report artifact; no email, public publishing or predicted revenue claims.",
        "width": 850,
        "height": 270
      }
    ],
    "edges": [
      {
        "source": "Daily company reporting",
        "target": "Compute tenant sales report",
        "branch": 0
      },
      {
        "source": "Compute tenant sales report",
        "target": "Build executive report artifact",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/report"
    ]
  },
  {
    "name": "MADAR Test Evaluation",
    "key": "madar-test-evaluation",
    "nodes": [
      {
        "id": "manual",
        "name": "Safe manual test",
        "type": "manualTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "evaluate-due-follow-ups",
        "name": "Evaluate due follow-ups",
        "type": "httpRequest",
        "position": [
          410,
          220
        ]
      },
      {
        "id": "read-operational-safeguards",
        "name": "Read operational safeguards",
        "type": "httpRequest",
        "position": [
          670,
          220
        ]
      },
      {
        "id": "local-acceptance",
        "name": "LOCAL ACCEPTANCE",
        "type": "stickyNote",
        "position": [
          110,
          100
        ],
        "note": "## LOCAL ACCEPTANCE\nQueues eligible records only. No dispatch, no activation, no paid inference.",
        "width": 800,
        "height": 250
      }
    ],
    "edges": [
      {
        "source": "Safe manual test",
        "target": "Evaluate due follow-ups",
        "branch": 0
      },
      {
        "source": "Evaluate due follow-ups",
        "target": "Read operational safeguards",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/tick",
      "/api/bridge/status"
    ]
  },
  {
    "name": "MADAR Viewing Reservations",
    "key": "madar-viewing-reservations",
    "nodes": [
      {
        "id": "sub",
        "name": "Called by workflow",
        "type": "executeWorkflowTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "validate-explicit-viewing-request",
        "name": "Validate explicit viewing request",
        "type": "code",
        "position": [
          410,
          220
        ]
      },
      {
        "id": "reserve-conflict-safe-appointment",
        "name": "Reserve conflict-safe appointment",
        "type": "httpRequest",
        "position": [
          680,
          220
        ]
      },
      {
        "id": "return-confirmed-crm-booking",
        "name": "Return confirmed CRM booking",
        "type": "code",
        "position": [
          980,
          220
        ]
      },
      {
        "id": "idempotent-reservation",
        "name": "IDEMPOTENT RESERVATION",
        "type": "stickyNote",
        "position": [
          110,
          90
        ],
        "note": "## IDEMPOTENT RESERVATION\nRequires an explicit customer, listing, adviser and timezone-aware future time. SQLite transaction prevents all resource overlaps; changed replay payloads conflict.",
        "width": 1120,
        "height": 270
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate explicit viewing request",
        "branch": 0
      },
      {
        "source": "Validate explicit viewing request",
        "target": "Reserve conflict-safe appointment",
        "branch": 0
      },
      {
        "source": "Reserve conflict-safe appointment",
        "target": "Return confirmed CRM booking",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/appointments"
    ]
  },
  {
    "name": "MADAR WhatsApp Delivery",
    "key": "madar-whatsapp-delivery",
    "nodes": [
      {
        "id": "manual",
        "name": "Operator delivery evaluation",
        "type": "manualTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "read-owner-delivery-authorization",
        "name": "Read owner delivery authorization",
        "type": "httpRequest",
        "position": [
          430,
          220
        ]
      },
      {
        "id": "real-delivery-explicitly-enabled",
        "name": "Real delivery explicitly enabled",
        "type": "if",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "dispatch-eligible-whatsapp-outbox",
        "name": "Dispatch eligible WhatsApp outbox",
        "type": "httpRequest",
        "position": [
          1010,
          110
        ]
      },
      {
        "id": "return-sandbox-boundary",
        "name": "Return sandbox boundary",
        "type": "code",
        "position": [
          1010,
          330
        ]
      },
      {
        "id": "official-meta-adapter",
        "name": "OFFICIAL META ADAPTER",
        "type": "stickyNote",
        "position": [
          110,
          70
        ],
        "note": "## OFFICIAL META ADAPTER\nCredentials stay in MADAR server settings. No Graph tokens in n8n exports. This workflow is inactive and starts only on operator evaluation.",
        "width": 770,
        "height": 300
      },
      {
        "id": "per-message-policy",
        "name": "PER-MESSAGE POLICY",
        "type": "stickyNote",
        "position": [
          910,
          30
        ],
        "note": "## PER-MESSAGE POLICY\nBackend enforces opt-out, proactive consent, 24-hour service window, template shape and sandbox contact blocking. Uncertain requests are never auto-retried.",
        "width": 360,
        "height": 460
      }
    ],
    "edges": [
      {
        "source": "Operator delivery evaluation",
        "target": "Read owner delivery authorization",
        "branch": 0
      },
      {
        "source": "Read owner delivery authorization",
        "target": "Real delivery explicitly enabled",
        "branch": 0
      },
      {
        "source": "Real delivery explicitly enabled",
        "target": "Dispatch eligible WhatsApp outbox",
        "branch": 0
      },
      {
        "source": "Real delivery explicitly enabled",
        "target": "Return sandbox boundary",
        "branch": 1
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/status",
      "/api/bridge/whatsapp/dispatch"
    ]
  }
];
