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
        "id": "sub",
        "name": "Called by workflow",
        "type": "executeWorkflowTrigger",
        "position": [
          160,
          220
        ]
      },
      {
        "id": "validate-orchestration-envelope",
        "name": "Validate orchestration envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "schedule",
        "name": "Every five minutes",
        "type": "scheduleTrigger",
        "position": [
          140,
          430
        ]
      },
      {
        "id": "generate-scheduled-receipt-identity",
        "name": "Generate scheduled receipt identity",
        "type": "code",
        "position": [
          140,
          650
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "validate-follow-up-interval",
        "name": "Validate follow-up interval",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "validate-follow-up-interval-accepted",
        "name": "Validate follow-up interval accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "validate-follow-up-interval-review-required",
        "name": "Validate follow-up interval review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "validate-company-timezone-configuration",
        "name": "Validate company timezone configuration",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "validate-company-timezone-configuration-accepted",
        "name": "Validate company timezone configuration accepted",
        "type": "if",
        "position": [
          1980,
          220
        ]
      },
      {
        "id": "validate-company-timezone-configuration-review-required",
        "name": "Validate company timezone configuration review required",
        "type": "code",
        "position": [
          1980,
          410
        ]
      },
      {
        "id": "collect-due-pending-tasks",
        "name": "Collect due pending tasks",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "exclude-missing-customer-references",
        "name": "Exclude missing customer references",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "exclude-missing-customer-references-accepted",
        "name": "Exclude missing customer references accepted",
        "type": "if",
        "position": [
          3280,
          220
        ]
      },
      {
        "id": "exclude-missing-customer-references-review-required",
        "name": "Exclude missing customer references review required",
        "type": "code",
        "position": [
          3280,
          410
        ]
      },
      {
        "id": "apply-customer-follow-up-consent",
        "name": "Apply customer follow-up consent",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "exclude-human-owned-conversations",
        "name": "Exclude human-owned conversations",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "identify-availability-follow-ups",
        "name": "Identify availability follow-ups",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "identify-ordinary-follow-ups",
        "name": "Identify ordinary follow-ups",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "collect-upcoming-viewing-reminders",
        "name": "Collect upcoming viewing reminders",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "identify-dormant-customer-re-engagement",
        "name": "Identify dormant customer re-engagement",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "identify-consented-customer-retention",
        "name": "Identify consented customer retention",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "validate-opt-out-suppression",
        "name": "Validate opt-out suppression",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "validate-opt-out-suppression-accepted",
        "name": "Validate opt-out suppression accepted",
        "type": "if",
        "position": [
          3280,
          1320
        ]
      },
      {
        "id": "validate-opt-out-suppression-review-required",
        "name": "Validate opt-out suppression review required",
        "type": "code",
        "position": [
          3280,
          1510
        ]
      },
      {
        "id": "validate-human-ownership-suppression",
        "name": "Validate human ownership suppression",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "validate-human-ownership-suppression-accepted",
        "name": "Validate human ownership suppression accepted",
        "type": "if",
        "position": [
          1330,
          1870
        ]
      },
      {
        "id": "validate-human-ownership-suppression-review-required",
        "name": "Validate human ownership suppression review required",
        "type": "code",
        "position": [
          1330,
          2060
        ]
      },
      {
        "id": "validate-delivery-authorization-type",
        "name": "Validate delivery authorization type",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "validate-delivery-authorization-type-accepted",
        "name": "Validate delivery authorization type accepted",
        "type": "if",
        "position": [
          1980,
          1870
        ]
      },
      {
        "id": "validate-delivery-authorization-type-review-required",
        "name": "Validate delivery authorization type review required",
        "type": "code",
        "position": [
          1980,
          2060
        ]
      },
      {
        "id": "prepare-stable-task-receipt-keys",
        "name": "Prepare stable task receipt keys",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "build-queue-only-follow-up-policy",
        "name": "Build queue-only follow-up policy",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "commit-authoritative-followup",
        "name": "Commit authoritative followup",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "return-minimal-orchestration-receipt",
        "name": "Return minimal orchestration receipt",
        "type": "code",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Every five minutes",
        "target": "Generate scheduled receipt identity",
        "branch": 0
      },
      {
        "source": "Generate scheduled receipt identity",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Validate orchestration envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Validate follow-up interval",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Validate follow-up interval",
        "target": "Validate follow-up interval accepted",
        "branch": 0
      },
      {
        "source": "Validate follow-up interval accepted",
        "target": "Validate company timezone configuration",
        "branch": 0
      },
      {
        "source": "Validate follow-up interval accepted",
        "target": "Validate follow-up interval review required",
        "branch": 1
      },
      {
        "source": "Validate follow-up interval review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate company timezone configuration",
        "target": "Validate company timezone configuration accepted",
        "branch": 0
      },
      {
        "source": "Validate company timezone configuration accepted",
        "target": "Collect due pending tasks",
        "branch": 0
      },
      {
        "source": "Validate company timezone configuration accepted",
        "target": "Validate company timezone configuration review required",
        "branch": 1
      },
      {
        "source": "Validate company timezone configuration review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Collect due pending tasks",
        "target": "Exclude missing customer references",
        "branch": 0
      },
      {
        "source": "Exclude missing customer references",
        "target": "Exclude missing customer references accepted",
        "branch": 0
      },
      {
        "source": "Exclude missing customer references accepted",
        "target": "Apply customer follow-up consent",
        "branch": 0
      },
      {
        "source": "Exclude missing customer references accepted",
        "target": "Exclude missing customer references review required",
        "branch": 1
      },
      {
        "source": "Exclude missing customer references review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Apply customer follow-up consent",
        "target": "Exclude human-owned conversations",
        "branch": 0
      },
      {
        "source": "Exclude human-owned conversations",
        "target": "Identify availability follow-ups",
        "branch": 0
      },
      {
        "source": "Identify availability follow-ups",
        "target": "Identify ordinary follow-ups",
        "branch": 0
      },
      {
        "source": "Identify ordinary follow-ups",
        "target": "Collect upcoming viewing reminders",
        "branch": 0
      },
      {
        "source": "Collect upcoming viewing reminders",
        "target": "Identify dormant customer re-engagement",
        "branch": 0
      },
      {
        "source": "Identify dormant customer re-engagement",
        "target": "Identify consented customer retention",
        "branch": 0
      },
      {
        "source": "Identify consented customer retention",
        "target": "Validate opt-out suppression",
        "branch": 0
      },
      {
        "source": "Validate opt-out suppression",
        "target": "Validate opt-out suppression accepted",
        "branch": 0
      },
      {
        "source": "Validate opt-out suppression accepted",
        "target": "Validate human ownership suppression",
        "branch": 0
      },
      {
        "source": "Validate opt-out suppression accepted",
        "target": "Validate opt-out suppression review required",
        "branch": 1
      },
      {
        "source": "Validate opt-out suppression review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate human ownership suppression",
        "target": "Validate human ownership suppression accepted",
        "branch": 0
      },
      {
        "source": "Validate human ownership suppression accepted",
        "target": "Validate delivery authorization type",
        "branch": 0
      },
      {
        "source": "Validate human ownership suppression accepted",
        "target": "Validate human ownership suppression review required",
        "branch": 1
      },
      {
        "source": "Validate human ownership suppression review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate delivery authorization type",
        "target": "Validate delivery authorization type accepted",
        "branch": 0
      },
      {
        "source": "Validate delivery authorization type accepted",
        "target": "Prepare stable task receipt keys",
        "branch": 0
      },
      {
        "source": "Validate delivery authorization type accepted",
        "target": "Validate delivery authorization type review required",
        "branch": 1
      },
      {
        "source": "Validate delivery authorization type review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Prepare stable task receipt keys",
        "target": "Build queue-only follow-up policy",
        "branch": 0
      },
      {
        "source": "Build queue-only follow-up policy",
        "target": "Commit authoritative followup",
        "branch": 0
      },
      {
        "source": "Commit authoritative followup",
        "target": "Return minimal orchestration receipt",
        "branch": 0
      },
      {
        "source": "Commit authoritative followup",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
    ]
  },
  {
    "name": "MADAR Full Demo",
    "key": "madar-full-demo",
    "nodes": [
      {
        "id": "manual",
        "name": "Run queued fictional demo",
        "type": "manualTrigger",
        "position": [
          120,
          260
        ]
      },
      {
        "id": "claim-isolated-demo-capability",
        "name": "Claim isolated demo capability",
        "type": "httpRequest",
        "position": [
          400,
          260
        ]
      },
      {
        "id": "run-intake-module",
        "name": "Run intake module",
        "type": "executeWorkflow",
        "position": [
          750,
          260
        ]
      },
      {
        "id": "run-qualification-module",
        "name": "Run qualification module",
        "type": "executeWorkflow",
        "position": [
          1040,
          260
        ]
      },
      {
        "id": "run-matching-module",
        "name": "Run matching module",
        "type": "executeWorkflow",
        "position": [
          1330,
          260
        ]
      },
      {
        "id": "run-appointment-module",
        "name": "Run appointment module",
        "type": "executeWorkflow",
        "position": [
          1620,
          260
        ]
      },
      {
        "id": "run-followup-module",
        "name": "Run followup module",
        "type": "executeWorkflow",
        "position": [
          1910,
          260
        ]
      },
      {
        "id": "run-conversation-module",
        "name": "Run conversation module",
        "type": "executeWorkflow",
        "position": [
          2200,
          260
        ]
      },
      {
        "id": "run-handoff-module",
        "name": "Run handoff module",
        "type": "executeWorkflow",
        "position": [
          2490,
          260
        ]
      },
      {
        "id": "run-reporting-module",
        "name": "Run reporting module",
        "type": "executeWorkflow",
        "position": [
          2780,
          260
        ]
      },
      {
        "id": "record-actual-execution-reference",
        "name": "Record actual execution reference",
        "type": "httpRequest",
        "position": [
          3180,
          260
        ]
      },
      {
        "id": "isolated-demo-/-real-n8n-execution",
        "name": "ISOLATED DEMO / REAL N8N EXECUTION",
        "type": "stickyNote",
        "position": [
          80,
          100
        ],
        "note": "## ISOLATED DEMO / REAL N8N EXECUTION\nClaim one queued fictional workspace. Eight real business modules, scoped capability, ordered replay-safe artifacts. Backend never marks execution verified until n8n reports success. No provider dispatch or paid model calls.",
        "width": 3370,
        "height": 400
      }
    ],
    "edges": [
      {
        "source": "Run queued fictional demo",
        "target": "Claim isolated demo capability",
        "branch": 0
      },
      {
        "source": "Claim isolated demo capability",
        "target": "Run intake module",
        "branch": 0
      },
      {
        "source": "Run intake module",
        "target": "Run qualification module",
        "branch": 0
      },
      {
        "source": "Run qualification module",
        "target": "Run matching module",
        "branch": 0
      },
      {
        "source": "Run matching module",
        "target": "Run appointment module",
        "branch": 0
      },
      {
        "source": "Run appointment module",
        "target": "Run followup module",
        "branch": 0
      },
      {
        "source": "Run followup module",
        "target": "Run conversation module",
        "branch": 0
      },
      {
        "source": "Run conversation module",
        "target": "Run handoff module",
        "branch": 0
      },
      {
        "source": "Run handoff module",
        "target": "Run reporting module",
        "branch": 0
      },
      {
        "source": "Run reporting module",
        "target": "Record actual execution reference",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/demo/claim",
      "/api/bridge/demo/complete"
    ]
  },
  {
    "name": "MADAR Human Handoff & Escalation",
    "key": "madar-human-handoff-&-escalation",
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
        "id": "validate-orchestration-envelope",
        "name": "Validate orchestration envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "require-customer-escalation-reference",
        "name": "Require customer escalation reference",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "require-customer-escalation-reference-accepted",
        "name": "Require customer escalation reference accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "require-customer-escalation-reference-review-required",
        "name": "Require customer escalation reference review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "validate-escalation-score",
        "name": "Validate escalation score",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "validate-escalation-score-accepted",
        "name": "Validate escalation score accepted",
        "type": "if",
        "position": [
          1980,
          220
        ]
      },
      {
        "id": "validate-escalation-score-review-required",
        "name": "Validate escalation score review required",
        "type": "code",
        "position": [
          1980,
          410
        ]
      },
      {
        "id": "determine-escalation-priority",
        "name": "Determine escalation priority",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "determine-response-sla-duration",
        "name": "Determine response SLA duration",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "calculate-sla-due-timestamp",
        "name": "Calculate SLA due timestamp",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "collect-active-advisers",
        "name": "Collect active advisers",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "require-available-escalation-adviser",
        "name": "Require available escalation adviser",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "require-available-escalation-adviser-accepted",
        "name": "Require available escalation adviser accepted",
        "type": "if",
        "position": [
          2630,
          770
        ]
      },
      {
        "id": "require-available-escalation-adviser-review-required",
        "name": "Require available escalation adviser review required",
        "type": "code",
        "position": [
          2630,
          960
        ]
      },
      {
        "id": "measure-adviser-open-pipeline",
        "name": "Measure adviser open pipeline",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "resolve-existing-assigned-adviser",
        "name": "Resolve existing assigned adviser",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "require-active-assigned-owner",
        "name": "Require active assigned owner",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "require-active-assigned-owner-accepted",
        "name": "Require active assigned owner accepted",
        "type": "if",
        "position": [
          1980,
          1320
        ]
      },
      {
        "id": "require-active-assigned-owner-review-required",
        "name": "Require active assigned owner review required",
        "type": "code",
        "position": [
          1980,
          1510
        ]
      },
      {
        "id": "find-existing-handoff-task",
        "name": "Find existing handoff task",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "validate-handoff-task-uniqueness",
        "name": "Validate handoff task uniqueness",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "validate-handoff-task-uniqueness-accepted",
        "name": "Validate handoff task uniqueness accepted",
        "type": "if",
        "position": [
          3280,
          1320
        ]
      },
      {
        "id": "validate-handoff-task-uniqueness-review-required",
        "name": "Validate handoff task uniqueness review required",
        "type": "code",
        "position": [
          3280,
          1510
        ]
      },
      {
        "id": "collect-confirmed-viewing-context",
        "name": "Collect confirmed viewing context",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "summarize-recorded-customer-requirements",
        "name": "Summarize recorded customer requirements",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "validate-supported-ownership-state",
        "name": "Validate supported ownership state",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "validate-supported-ownership-state-accepted",
        "name": "Validate supported ownership state accepted",
        "type": "if",
        "position": [
          2630,
          1870
        ]
      },
      {
        "id": "validate-supported-ownership-state-review-required",
        "name": "Validate supported ownership state review required",
        "type": "code",
        "position": [
          2630,
          2060
        ]
      },
      {
        "id": "prepare-acknowledgement-and-resolution-policy",
        "name": "Prepare acknowledgement and resolution policy",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "commit-authoritative-handoff",
        "name": "Commit authoritative handoff",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "return-minimal-orchestration-receipt",
        "name": "Return minimal orchestration receipt",
        "type": "code",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Validate orchestration envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Require customer escalation reference",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Require customer escalation reference",
        "target": "Require customer escalation reference accepted",
        "branch": 0
      },
      {
        "source": "Require customer escalation reference accepted",
        "target": "Validate escalation score",
        "branch": 0
      },
      {
        "source": "Require customer escalation reference accepted",
        "target": "Require customer escalation reference review required",
        "branch": 1
      },
      {
        "source": "Require customer escalation reference review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate escalation score",
        "target": "Validate escalation score accepted",
        "branch": 0
      },
      {
        "source": "Validate escalation score accepted",
        "target": "Determine escalation priority",
        "branch": 0
      },
      {
        "source": "Validate escalation score accepted",
        "target": "Validate escalation score review required",
        "branch": 1
      },
      {
        "source": "Validate escalation score review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Determine escalation priority",
        "target": "Determine response SLA duration",
        "branch": 0
      },
      {
        "source": "Determine response SLA duration",
        "target": "Calculate SLA due timestamp",
        "branch": 0
      },
      {
        "source": "Calculate SLA due timestamp",
        "target": "Collect active advisers",
        "branch": 0
      },
      {
        "source": "Collect active advisers",
        "target": "Require available escalation adviser",
        "branch": 0
      },
      {
        "source": "Require available escalation adviser",
        "target": "Require available escalation adviser accepted",
        "branch": 0
      },
      {
        "source": "Require available escalation adviser accepted",
        "target": "Measure adviser open pipeline",
        "branch": 0
      },
      {
        "source": "Require available escalation adviser accepted",
        "target": "Require available escalation adviser review required",
        "branch": 1
      },
      {
        "source": "Require available escalation adviser review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Measure adviser open pipeline",
        "target": "Resolve existing assigned adviser",
        "branch": 0
      },
      {
        "source": "Resolve existing assigned adviser",
        "target": "Require active assigned owner",
        "branch": 0
      },
      {
        "source": "Require active assigned owner",
        "target": "Require active assigned owner accepted",
        "branch": 0
      },
      {
        "source": "Require active assigned owner accepted",
        "target": "Find existing handoff task",
        "branch": 0
      },
      {
        "source": "Require active assigned owner accepted",
        "target": "Require active assigned owner review required",
        "branch": 1
      },
      {
        "source": "Require active assigned owner review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Find existing handoff task",
        "target": "Validate handoff task uniqueness",
        "branch": 0
      },
      {
        "source": "Validate handoff task uniqueness",
        "target": "Validate handoff task uniqueness accepted",
        "branch": 0
      },
      {
        "source": "Validate handoff task uniqueness accepted",
        "target": "Collect confirmed viewing context",
        "branch": 0
      },
      {
        "source": "Validate handoff task uniqueness accepted",
        "target": "Validate handoff task uniqueness review required",
        "branch": 1
      },
      {
        "source": "Validate handoff task uniqueness review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Collect confirmed viewing context",
        "target": "Summarize recorded customer requirements",
        "branch": 0
      },
      {
        "source": "Summarize recorded customer requirements",
        "target": "Validate supported ownership state",
        "branch": 0
      },
      {
        "source": "Validate supported ownership state",
        "target": "Validate supported ownership state accepted",
        "branch": 0
      },
      {
        "source": "Validate supported ownership state accepted",
        "target": "Prepare acknowledgement and resolution policy",
        "branch": 0
      },
      {
        "source": "Validate supported ownership state accepted",
        "target": "Validate supported ownership state review required",
        "branch": 1
      },
      {
        "source": "Validate supported ownership state review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Prepare acknowledgement and resolution policy",
        "target": "Commit authoritative handoff",
        "branch": 0
      },
      {
        "source": "Commit authoritative handoff",
        "target": "Return minimal orchestration receipt",
        "branch": 0
      },
      {
        "source": "Commit authoritative handoff",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
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
        "id": "validate-orchestration-envelope",
        "name": "Validate orchestration envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "resolve-recorded-customer",
        "name": "Resolve recorded customer",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "resolve-recorded-customer-accepted",
        "name": "Resolve recorded customer accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "resolve-recorded-customer-review-required",
        "name": "Resolve recorded customer review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "validate-persisted-preference-bounds",
        "name": "Validate persisted preference bounds",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "validate-persisted-preference-bounds-accepted",
        "name": "Validate persisted preference bounds accepted",
        "type": "if",
        "position": [
          1980,
          220
        ]
      },
      {
        "id": "validate-persisted-preference-bounds-review-required",
        "name": "Validate persisted preference bounds review required",
        "type": "code",
        "position": [
          1980,
          410
        ]
      },
      {
        "id": "detect-preferred-conversation-language",
        "name": "Detect preferred conversation language",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "identify-missing-qualification-fields",
        "name": "Identify missing qualification fields",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "audit-budget-contribution",
        "name": "Audit budget contribution",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "audit-location-contribution",
        "name": "Audit location contribution",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "audit-specification-contribution",
        "name": "Audit specification contribution",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "audit-contact-and-consent-contribution",
        "name": "Audit contact and consent contribution",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "reconcile-persisted-qualification-score",
        "name": "Reconcile persisted qualification score",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "reconcile-persisted-qualification-score-accepted",
        "name": "Reconcile persisted qualification score accepted",
        "type": "if",
        "position": [
          1330,
          1320
        ]
      },
      {
        "id": "reconcile-persisted-qualification-score-review-required",
        "name": "Reconcile persisted qualification score review required",
        "type": "code",
        "position": [
          1330,
          1510
        ]
      },
      {
        "id": "detect-viewing-intent-evidence",
        "name": "Detect viewing intent evidence",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "detect-urgency-evidence",
        "name": "Detect urgency evidence",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "determine-authoritative-ownership",
        "name": "Determine authoritative ownership",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "validate-assigned-adviser-membership",
        "name": "Validate assigned adviser membership",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "validate-assigned-adviser-membership-accepted",
        "name": "Validate assigned adviser membership accepted",
        "type": "if",
        "position": [
          1330,
          1870
        ]
      },
      {
        "id": "validate-assigned-adviser-membership-review-required",
        "name": "Validate assigned adviser membership review required",
        "type": "code",
        "position": [
          1330,
          2060
        ]
      },
      {
        "id": "validate-qualification-enum-values",
        "name": "Validate qualification enum values",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "validate-qualification-enum-values-accepted",
        "name": "Validate qualification enum values accepted",
        "type": "if",
        "position": [
          1980,
          1870
        ]
      },
      {
        "id": "validate-qualification-enum-values-review-required",
        "name": "Validate qualification enum values review required",
        "type": "code",
        "position": [
          1980,
          2060
        ]
      },
      {
        "id": "require-available-qualification-evidence",
        "name": "Require available qualification evidence",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "require-available-qualification-evidence-accepted",
        "name": "Require available qualification evidence accepted",
        "type": "if",
        "position": [
          2630,
          1870
        ]
      },
      {
        "id": "require-available-qualification-evidence-review-required",
        "name": "Require available qualification evidence review required",
        "type": "code",
        "position": [
          2630,
          2060
        ]
      },
      {
        "id": "choose-safe-sales-readiness",
        "name": "Choose safe sales readiness",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "commit-authoritative-qualification",
        "name": "Commit authoritative qualification",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "return-minimal-orchestration-receipt",
        "name": "Return minimal orchestration receipt",
        "type": "code",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Validate orchestration envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Resolve recorded customer",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Resolve recorded customer",
        "target": "Resolve recorded customer accepted",
        "branch": 0
      },
      {
        "source": "Resolve recorded customer accepted",
        "target": "Validate persisted preference bounds",
        "branch": 0
      },
      {
        "source": "Resolve recorded customer accepted",
        "target": "Resolve recorded customer review required",
        "branch": 1
      },
      {
        "source": "Resolve recorded customer review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate persisted preference bounds",
        "target": "Validate persisted preference bounds accepted",
        "branch": 0
      },
      {
        "source": "Validate persisted preference bounds accepted",
        "target": "Detect preferred conversation language",
        "branch": 0
      },
      {
        "source": "Validate persisted preference bounds accepted",
        "target": "Validate persisted preference bounds review required",
        "branch": 1
      },
      {
        "source": "Validate persisted preference bounds review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Detect preferred conversation language",
        "target": "Identify missing qualification fields",
        "branch": 0
      },
      {
        "source": "Identify missing qualification fields",
        "target": "Audit budget contribution",
        "branch": 0
      },
      {
        "source": "Audit budget contribution",
        "target": "Audit location contribution",
        "branch": 0
      },
      {
        "source": "Audit location contribution",
        "target": "Audit specification contribution",
        "branch": 0
      },
      {
        "source": "Audit specification contribution",
        "target": "Audit contact and consent contribution",
        "branch": 0
      },
      {
        "source": "Audit contact and consent contribution",
        "target": "Reconcile persisted qualification score",
        "branch": 0
      },
      {
        "source": "Reconcile persisted qualification score",
        "target": "Reconcile persisted qualification score accepted",
        "branch": 0
      },
      {
        "source": "Reconcile persisted qualification score accepted",
        "target": "Detect viewing intent evidence",
        "branch": 0
      },
      {
        "source": "Reconcile persisted qualification score accepted",
        "target": "Reconcile persisted qualification score review required",
        "branch": 1
      },
      {
        "source": "Reconcile persisted qualification score review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Detect viewing intent evidence",
        "target": "Detect urgency evidence",
        "branch": 0
      },
      {
        "source": "Detect urgency evidence",
        "target": "Determine authoritative ownership",
        "branch": 0
      },
      {
        "source": "Determine authoritative ownership",
        "target": "Validate assigned adviser membership",
        "branch": 0
      },
      {
        "source": "Validate assigned adviser membership",
        "target": "Validate assigned adviser membership accepted",
        "branch": 0
      },
      {
        "source": "Validate assigned adviser membership accepted",
        "target": "Validate qualification enum values",
        "branch": 0
      },
      {
        "source": "Validate assigned adviser membership accepted",
        "target": "Validate assigned adviser membership review required",
        "branch": 1
      },
      {
        "source": "Validate assigned adviser membership review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate qualification enum values",
        "target": "Validate qualification enum values accepted",
        "branch": 0
      },
      {
        "source": "Validate qualification enum values accepted",
        "target": "Require available qualification evidence",
        "branch": 0
      },
      {
        "source": "Validate qualification enum values accepted",
        "target": "Validate qualification enum values review required",
        "branch": 1
      },
      {
        "source": "Validate qualification enum values review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Require available qualification evidence",
        "target": "Require available qualification evidence accepted",
        "branch": 0
      },
      {
        "source": "Require available qualification evidence accepted",
        "target": "Choose safe sales readiness",
        "branch": 0
      },
      {
        "source": "Require available qualification evidence accepted",
        "target": "Require available qualification evidence review required",
        "branch": 1
      },
      {
        "source": "Require available qualification evidence review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Choose safe sales readiness",
        "target": "Commit authoritative qualification",
        "branch": 0
      },
      {
        "source": "Commit authoritative qualification",
        "target": "Return minimal orchestration receipt",
        "branch": 0
      },
      {
        "source": "Commit authoritative qualification",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
    ]
  },
  {
    "name": "MADAR Omnichannel Intake",
    "key": "madar-omnichannel-intake",
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
        "id": "normalize-trusted-envelope",
        "name": "Normalize trusted envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "intake-webhook",
        "name": "Authenticated normalized events",
        "type": "webhook",
        "position": [
          140,
          430
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "validate-event-identity",
        "name": "Validate event identity",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "validate-event-identity-accepted",
        "name": "Validate event identity accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "validate-event-identity-review-required",
        "name": "Validate event identity review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "validate-customer-name",
        "name": "Validate customer name",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "validate-customer-name-accepted",
        "name": "Validate customer name accepted",
        "type": "if",
        "position": [
          1980,
          220
        ]
      },
      {
        "id": "validate-customer-name-review-required",
        "name": "Validate customer name review required",
        "type": "code",
        "position": [
          1980,
          410
        ]
      },
      {
        "id": "validate-message-size",
        "name": "Validate message size",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "validate-message-size-accepted",
        "name": "Validate message size accepted",
        "type": "if",
        "position": [
          2630,
          220
        ]
      },
      {
        "id": "validate-message-size-review-required",
        "name": "Validate message size review required",
        "type": "code",
        "position": [
          2630,
          410
        ]
      },
      {
        "id": "authorize-supported-source",
        "name": "Authorize supported source",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "authorize-supported-source-accepted",
        "name": "Authorize supported source accepted",
        "type": "if",
        "position": [
          3280,
          220
        ]
      },
      {
        "id": "authorize-supported-source-review-required",
        "name": "Authorize supported source review required",
        "type": "code",
        "position": [
          3280,
          410
        ]
      },
      {
        "id": "normalize-contact-phone",
        "name": "Normalize contact phone",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "normalize-contact-email",
        "name": "Normalize contact email",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "resolve-contact-identity-collisions",
        "name": "Resolve contact identity collisions",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "resolve-contact-identity-collisions-accepted",
        "name": "Resolve contact identity collisions accepted",
        "type": "if",
        "position": [
          2630,
          770
        ]
      },
      {
        "id": "resolve-contact-identity-collisions-review-required",
        "name": "Resolve contact identity collisions review required",
        "type": "code",
        "position": [
          2630,
          960
        ]
      },
      {
        "id": "detect-explicit-arabic-or-english",
        "name": "Detect explicit Arabic or English",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "detect-customer-opt-out",
        "name": "Detect customer opt-out",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "verify-literal-consent-flag",
        "name": "Verify literal consent flag",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "identify-injection-review-signals",
        "name": "Identify injection review signals",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "calculate-preference-completeness",
        "name": "Calculate preference completeness",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "measure-active-adviser-workload",
        "name": "Measure active adviser workload",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "require-an-available-adviser",
        "name": "Require an available adviser",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "require-an-available-adviser-accepted",
        "name": "Require an available adviser accepted",
        "type": "if",
        "position": [
          1980,
          1870
        ]
      },
      {
        "id": "require-an-available-adviser-review-required",
        "name": "Require an available adviser review required",
        "type": "code",
        "position": [
          1980,
          2060
        ]
      },
      {
        "id": "plan-consent-aware-intake-follow-up",
        "name": "Plan consent-aware intake follow-up",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "prepare-atomic-crm-disposition",
        "name": "Prepare atomic CRM disposition",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "commit-authoritative-intake",
        "name": "Commit authoritative intake",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "new-event-requires-intelligence",
        "name": "New event requires intelligence",
        "type": "if",
        "position": [
          4050,
          1700
        ]
      },
      {
        "id": "resolve-sales-intelligence",
        "name": "Resolve sales intelligence",
        "type": "executeWorkflow",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "http-request-requires-acknowledgement",
        "name": "HTTP request requires acknowledgement",
        "type": "if",
        "position": [
          4380,
          1870
        ]
      },
      {
        "id": "acknowledge-accepted-event",
        "name": "Acknowledge accepted event",
        "type": "respondToWebhook",
        "position": [
          4670,
          1780
        ]
      },
      {
        "id": "return-scoped-module-result",
        "name": "Return scoped module result",
        "type": "code",
        "position": [
          4670,
          1990
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Normalize trusted envelope",
        "branch": 0
      },
      {
        "source": "Authenticated normalized events",
        "target": "Normalize trusted envelope",
        "branch": 0
      },
      {
        "source": "Normalize trusted envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Validate event identity",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Validate event identity",
        "target": "Validate event identity accepted",
        "branch": 0
      },
      {
        "source": "Validate event identity accepted",
        "target": "Validate customer name",
        "branch": 0
      },
      {
        "source": "Validate event identity accepted",
        "target": "Validate event identity review required",
        "branch": 1
      },
      {
        "source": "Validate event identity review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate customer name",
        "target": "Validate customer name accepted",
        "branch": 0
      },
      {
        "source": "Validate customer name accepted",
        "target": "Validate message size",
        "branch": 0
      },
      {
        "source": "Validate customer name accepted",
        "target": "Validate customer name review required",
        "branch": 1
      },
      {
        "source": "Validate customer name review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate message size",
        "target": "Validate message size accepted",
        "branch": 0
      },
      {
        "source": "Validate message size accepted",
        "target": "Authorize supported source",
        "branch": 0
      },
      {
        "source": "Validate message size accepted",
        "target": "Validate message size review required",
        "branch": 1
      },
      {
        "source": "Validate message size review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Authorize supported source",
        "target": "Authorize supported source accepted",
        "branch": 0
      },
      {
        "source": "Authorize supported source accepted",
        "target": "Normalize contact phone",
        "branch": 0
      },
      {
        "source": "Authorize supported source accepted",
        "target": "Authorize supported source review required",
        "branch": 1
      },
      {
        "source": "Authorize supported source review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Normalize contact phone",
        "target": "Normalize contact email",
        "branch": 0
      },
      {
        "source": "Normalize contact email",
        "target": "Resolve contact identity collisions",
        "branch": 0
      },
      {
        "source": "Resolve contact identity collisions",
        "target": "Resolve contact identity collisions accepted",
        "branch": 0
      },
      {
        "source": "Resolve contact identity collisions accepted",
        "target": "Detect explicit Arabic or English",
        "branch": 0
      },
      {
        "source": "Resolve contact identity collisions accepted",
        "target": "Resolve contact identity collisions review required",
        "branch": 1
      },
      {
        "source": "Resolve contact identity collisions review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Detect explicit Arabic or English",
        "target": "Detect customer opt-out",
        "branch": 0
      },
      {
        "source": "Detect customer opt-out",
        "target": "Verify literal consent flag",
        "branch": 0
      },
      {
        "source": "Verify literal consent flag",
        "target": "Identify injection review signals",
        "branch": 0
      },
      {
        "source": "Identify injection review signals",
        "target": "Calculate preference completeness",
        "branch": 0
      },
      {
        "source": "Calculate preference completeness",
        "target": "Measure active adviser workload",
        "branch": 0
      },
      {
        "source": "Measure active adviser workload",
        "target": "Require an available adviser",
        "branch": 0
      },
      {
        "source": "Require an available adviser",
        "target": "Require an available adviser accepted",
        "branch": 0
      },
      {
        "source": "Require an available adviser accepted",
        "target": "Plan consent-aware intake follow-up",
        "branch": 0
      },
      {
        "source": "Require an available adviser accepted",
        "target": "Require an available adviser review required",
        "branch": 1
      },
      {
        "source": "Require an available adviser review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Plan consent-aware intake follow-up",
        "target": "Prepare atomic CRM disposition",
        "branch": 0
      },
      {
        "source": "Prepare atomic CRM disposition",
        "target": "Commit authoritative intake",
        "branch": 0
      },
      {
        "source": "Commit authoritative intake",
        "target": "New event requires intelligence",
        "branch": 0
      },
      {
        "source": "Commit authoritative intake",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      },
      {
        "source": "New event requires intelligence",
        "target": "Resolve sales intelligence",
        "branch": 0
      },
      {
        "source": "New event requires intelligence",
        "target": "HTTP request requires acknowledgement",
        "branch": 1
      },
      {
        "source": "Resolve sales intelligence",
        "target": "HTTP request requires acknowledgement",
        "branch": 0
      },
      {
        "source": "HTTP request requires acknowledgement",
        "target": "Acknowledge accepted event",
        "branch": 0
      },
      {
        "source": "HTTP request requires acknowledgement",
        "target": "Return scoped module result",
        "branch": 1
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
    ]
  },
  {
    "name": "MADAR Property Matching Engine",
    "key": "madar-property-matching-engine",
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
        "id": "validate-orchestration-envelope",
        "name": "Validate orchestration envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "require-customer-inventory-context",
        "name": "Require customer inventory context",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "require-customer-inventory-context-accepted",
        "name": "Require customer inventory context accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "require-customer-inventory-context-review-required",
        "name": "Require customer inventory context review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "validate-inventory-prices",
        "name": "Validate inventory prices",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "validate-inventory-prices-accepted",
        "name": "Validate inventory prices accepted",
        "type": "if",
        "position": [
          1980,
          220
        ]
      },
      {
        "id": "validate-inventory-prices-review-required",
        "name": "Validate inventory prices review required",
        "type": "code",
        "position": [
          1980,
          410
        ]
      },
      {
        "id": "filter-currently-available-inventory",
        "name": "Filter currently available inventory",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "filter-transaction-intent",
        "name": "Filter transaction intent",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "apply-hard-budget-constraint",
        "name": "Apply hard budget constraint",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "apply-hard-area-constraint",
        "name": "Apply hard area constraint",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "apply-hard-property-category",
        "name": "Apply hard property category",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "apply-minimum-bedrooms",
        "name": "Apply minimum bedrooms",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "apply-minimum-floor-area",
        "name": "Apply minimum floor area",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "evaluate-requested-amenities",
        "name": "Evaluate requested amenities",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "verify-recommendation-ownership",
        "name": "Verify recommendation ownership",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "verify-recommendation-ownership-accepted",
        "name": "Verify recommendation ownership accepted",
        "type": "if",
        "position": [
          2630,
          1320
        ]
      },
      {
        "id": "verify-recommendation-ownership-review-required",
        "name": "Verify recommendation ownership review required",
        "type": "code",
        "position": [
          2630,
          1510
        ]
      },
      {
        "id": "verify-recommendation-availability",
        "name": "Verify recommendation availability",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "verify-recommendation-availability-accepted",
        "name": "Verify recommendation availability accepted",
        "type": "if",
        "position": [
          3280,
          1320
        ]
      },
      {
        "id": "verify-recommendation-availability-review-required",
        "name": "Verify recommendation availability review required",
        "type": "code",
        "position": [
          3280,
          1510
        ]
      },
      {
        "id": "verify-recommendations-respect-budget",
        "name": "Verify recommendations respect budget",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "verify-recommendations-respect-budget-accepted",
        "name": "Verify recommendations respect budget accepted",
        "type": "if",
        "position": [
          1330,
          1870
        ]
      },
      {
        "id": "verify-recommendations-respect-budget-review-required",
        "name": "Verify recommendations respect budget review required",
        "type": "code",
        "position": [
          1330,
          2060
        ]
      },
      {
        "id": "verify-recommendations-respect-transaction",
        "name": "Verify recommendations respect transaction",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "verify-recommendations-respect-transaction-accepted",
        "name": "Verify recommendations respect transaction accepted",
        "type": "if",
        "position": [
          1980,
          1870
        ]
      },
      {
        "id": "verify-recommendations-respect-transaction-review-required",
        "name": "Verify recommendations respect transaction review required",
        "type": "code",
        "position": [
          1980,
          2060
        ]
      },
      {
        "id": "explain-inventory-rejection-funnel",
        "name": "Explain inventory rejection funnel",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "prepare-honest-no-match-alternatives",
        "name": "Prepare honest no-match alternatives",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "commit-authoritative-matching",
        "name": "Commit authoritative matching",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "return-minimal-orchestration-receipt",
        "name": "Return minimal orchestration receipt",
        "type": "code",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Validate orchestration envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Require customer inventory context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Require customer inventory context",
        "target": "Require customer inventory context accepted",
        "branch": 0
      },
      {
        "source": "Require customer inventory context accepted",
        "target": "Validate inventory prices",
        "branch": 0
      },
      {
        "source": "Require customer inventory context accepted",
        "target": "Require customer inventory context review required",
        "branch": 1
      },
      {
        "source": "Require customer inventory context review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate inventory prices",
        "target": "Validate inventory prices accepted",
        "branch": 0
      },
      {
        "source": "Validate inventory prices accepted",
        "target": "Filter currently available inventory",
        "branch": 0
      },
      {
        "source": "Validate inventory prices accepted",
        "target": "Validate inventory prices review required",
        "branch": 1
      },
      {
        "source": "Validate inventory prices review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Filter currently available inventory",
        "target": "Filter transaction intent",
        "branch": 0
      },
      {
        "source": "Filter transaction intent",
        "target": "Apply hard budget constraint",
        "branch": 0
      },
      {
        "source": "Apply hard budget constraint",
        "target": "Apply hard area constraint",
        "branch": 0
      },
      {
        "source": "Apply hard area constraint",
        "target": "Apply hard property category",
        "branch": 0
      },
      {
        "source": "Apply hard property category",
        "target": "Apply minimum bedrooms",
        "branch": 0
      },
      {
        "source": "Apply minimum bedrooms",
        "target": "Apply minimum floor area",
        "branch": 0
      },
      {
        "source": "Apply minimum floor area",
        "target": "Evaluate requested amenities",
        "branch": 0
      },
      {
        "source": "Evaluate requested amenities",
        "target": "Verify recommendation ownership",
        "branch": 0
      },
      {
        "source": "Verify recommendation ownership",
        "target": "Verify recommendation ownership accepted",
        "branch": 0
      },
      {
        "source": "Verify recommendation ownership accepted",
        "target": "Verify recommendation availability",
        "branch": 0
      },
      {
        "source": "Verify recommendation ownership accepted",
        "target": "Verify recommendation ownership review required",
        "branch": 1
      },
      {
        "source": "Verify recommendation ownership review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Verify recommendation availability",
        "target": "Verify recommendation availability accepted",
        "branch": 0
      },
      {
        "source": "Verify recommendation availability accepted",
        "target": "Verify recommendations respect budget",
        "branch": 0
      },
      {
        "source": "Verify recommendation availability accepted",
        "target": "Verify recommendation availability review required",
        "branch": 1
      },
      {
        "source": "Verify recommendation availability review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Verify recommendations respect budget",
        "target": "Verify recommendations respect budget accepted",
        "branch": 0
      },
      {
        "source": "Verify recommendations respect budget accepted",
        "target": "Verify recommendations respect transaction",
        "branch": 0
      },
      {
        "source": "Verify recommendations respect budget accepted",
        "target": "Verify recommendations respect budget review required",
        "branch": 1
      },
      {
        "source": "Verify recommendations respect budget review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Verify recommendations respect transaction",
        "target": "Verify recommendations respect transaction accepted",
        "branch": 0
      },
      {
        "source": "Verify recommendations respect transaction accepted",
        "target": "Explain inventory rejection funnel",
        "branch": 0
      },
      {
        "source": "Verify recommendations respect transaction accepted",
        "target": "Verify recommendations respect transaction review required",
        "branch": 1
      },
      {
        "source": "Verify recommendations respect transaction review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Explain inventory rejection funnel",
        "target": "Prepare honest no-match alternatives",
        "branch": 0
      },
      {
        "source": "Prepare honest no-match alternatives",
        "target": "Commit authoritative matching",
        "branch": 0
      },
      {
        "source": "Commit authoritative matching",
        "target": "Return minimal orchestration receipt",
        "branch": 0
      },
      {
        "source": "Commit authoritative matching",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
    ]
  },
  {
    "name": "MADAR Sales Reporting",
    "key": "madar-sales-reporting",
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
        "id": "validate-orchestration-envelope",
        "name": "Validate orchestration envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "schedule",
        "name": "Daily company reporting",
        "type": "scheduleTrigger",
        "position": [
          140,
          430
        ]
      },
      {
        "id": "generate-scheduled-receipt-identity",
        "name": "Generate scheduled receipt identity",
        "type": "code",
        "position": [
          140,
          650
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "validate-crm-stage-values",
        "name": "Validate CRM stage values",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "validate-crm-stage-values-accepted",
        "name": "Validate CRM stage values accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "validate-crm-stage-values-review-required",
        "name": "Validate CRM stage values review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "validate-recorded-commission-amounts",
        "name": "Validate recorded commission amounts",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "validate-recorded-commission-amounts-accepted",
        "name": "Validate recorded commission amounts accepted",
        "type": "if",
        "position": [
          1980,
          220
        ]
      },
      {
        "id": "validate-recorded-commission-amounts-review-required",
        "name": "Validate recorded commission amounts review required",
        "type": "code",
        "position": [
          1980,
          410
        ]
      },
      {
        "id": "count-recorded-customer-pipeline",
        "name": "Count recorded customer pipeline",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "measure-channel-acquisition",
        "name": "Measure channel acquisition",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "measure-qualified-opportunity-count",
        "name": "Measure qualified opportunity count",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "measure-closed-won-conversion",
        "name": "Measure closed-won conversion",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "separate-earned-commission-revenue",
        "name": "Separate earned commission revenue",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "measure-recorded-sales-volume",
        "name": "Measure recorded sales volume",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "separate-open-pipeline-from-earnings",
        "name": "Separate open pipeline from earnings",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "measure-viewing-completion",
        "name": "Measure viewing completion",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "measure-adviser-conversion",
        "name": "Measure adviser conversion",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "validate-tenant-customer-references",
        "name": "Validate tenant customer references",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "validate-tenant-customer-references-accepted",
        "name": "Validate tenant customer references accepted",
        "type": "if",
        "position": [
          3280,
          1320
        ]
      },
      {
        "id": "validate-tenant-customer-references-review-required",
        "name": "Validate tenant customer references review required",
        "type": "code",
        "position": [
          3280,
          1510
        ]
      },
      {
        "id": "measure-unresolved-follow-up-backlog",
        "name": "Measure unresolved follow-up backlog",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "validate-report-currency-representation",
        "name": "Validate report currency representation",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "validate-report-currency-representation-accepted",
        "name": "Validate report currency representation accepted",
        "type": "if",
        "position": [
          1980,
          1870
        ]
      },
      {
        "id": "validate-report-currency-representation-review-required",
        "name": "Validate report currency representation review required",
        "type": "code",
        "position": [
          1980,
          2060
        ]
      },
      {
        "id": "validate-report-percentage-bounds",
        "name": "Validate report percentage bounds",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "validate-report-percentage-bounds-accepted",
        "name": "Validate report percentage bounds accepted",
        "type": "if",
        "position": [
          2630,
          1870
        ]
      },
      {
        "id": "validate-report-percentage-bounds-review-required",
        "name": "Validate report percentage bounds review required",
        "type": "code",
        "position": [
          2630,
          2060
        ]
      },
      {
        "id": "require-timestamped-measurement-evidence",
        "name": "Require timestamped measurement evidence",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "require-timestamped-measurement-evidence-accepted",
        "name": "Require timestamped measurement evidence accepted",
        "type": "if",
        "position": [
          3280,
          1870
        ]
      },
      {
        "id": "require-timestamped-measurement-evidence-review-required",
        "name": "Require timestamped measurement evidence review required",
        "type": "code",
        "position": [
          3280,
          2060
        ]
      },
      {
        "id": "commit-authoritative-reporting",
        "name": "Commit authoritative reporting",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "return-minimal-orchestration-receipt",
        "name": "Return minimal orchestration receipt",
        "type": "code",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Daily company reporting",
        "target": "Generate scheduled receipt identity",
        "branch": 0
      },
      {
        "source": "Generate scheduled receipt identity",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Validate orchestration envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Validate CRM stage values",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Validate CRM stage values",
        "target": "Validate CRM stage values accepted",
        "branch": 0
      },
      {
        "source": "Validate CRM stage values accepted",
        "target": "Validate recorded commission amounts",
        "branch": 0
      },
      {
        "source": "Validate CRM stage values accepted",
        "target": "Validate CRM stage values review required",
        "branch": 1
      },
      {
        "source": "Validate CRM stage values review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate recorded commission amounts",
        "target": "Validate recorded commission amounts accepted",
        "branch": 0
      },
      {
        "source": "Validate recorded commission amounts accepted",
        "target": "Count recorded customer pipeline",
        "branch": 0
      },
      {
        "source": "Validate recorded commission amounts accepted",
        "target": "Validate recorded commission amounts review required",
        "branch": 1
      },
      {
        "source": "Validate recorded commission amounts review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Count recorded customer pipeline",
        "target": "Measure channel acquisition",
        "branch": 0
      },
      {
        "source": "Measure channel acquisition",
        "target": "Measure qualified opportunity count",
        "branch": 0
      },
      {
        "source": "Measure qualified opportunity count",
        "target": "Measure closed-won conversion",
        "branch": 0
      },
      {
        "source": "Measure closed-won conversion",
        "target": "Separate earned commission revenue",
        "branch": 0
      },
      {
        "source": "Separate earned commission revenue",
        "target": "Measure recorded sales volume",
        "branch": 0
      },
      {
        "source": "Measure recorded sales volume",
        "target": "Separate open pipeline from earnings",
        "branch": 0
      },
      {
        "source": "Separate open pipeline from earnings",
        "target": "Measure viewing completion",
        "branch": 0
      },
      {
        "source": "Measure viewing completion",
        "target": "Measure adviser conversion",
        "branch": 0
      },
      {
        "source": "Measure adviser conversion",
        "target": "Validate tenant customer references",
        "branch": 0
      },
      {
        "source": "Validate tenant customer references",
        "target": "Validate tenant customer references accepted",
        "branch": 0
      },
      {
        "source": "Validate tenant customer references accepted",
        "target": "Measure unresolved follow-up backlog",
        "branch": 0
      },
      {
        "source": "Validate tenant customer references accepted",
        "target": "Validate tenant customer references review required",
        "branch": 1
      },
      {
        "source": "Validate tenant customer references review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Measure unresolved follow-up backlog",
        "target": "Validate report currency representation",
        "branch": 0
      },
      {
        "source": "Validate report currency representation",
        "target": "Validate report currency representation accepted",
        "branch": 0
      },
      {
        "source": "Validate report currency representation accepted",
        "target": "Validate report percentage bounds",
        "branch": 0
      },
      {
        "source": "Validate report currency representation accepted",
        "target": "Validate report currency representation review required",
        "branch": 1
      },
      {
        "source": "Validate report currency representation review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate report percentage bounds",
        "target": "Validate report percentage bounds accepted",
        "branch": 0
      },
      {
        "source": "Validate report percentage bounds accepted",
        "target": "Require timestamped measurement evidence",
        "branch": 0
      },
      {
        "source": "Validate report percentage bounds accepted",
        "target": "Validate report percentage bounds review required",
        "branch": 1
      },
      {
        "source": "Validate report percentage bounds review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Require timestamped measurement evidence",
        "target": "Require timestamped measurement evidence accepted",
        "branch": 0
      },
      {
        "source": "Require timestamped measurement evidence accepted",
        "target": "Commit authoritative reporting",
        "branch": 0
      },
      {
        "source": "Require timestamped measurement evidence accepted",
        "target": "Require timestamped measurement evidence review required",
        "branch": 1
      },
      {
        "source": "Require timestamped measurement evidence review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Commit authoritative reporting",
        "target": "Return minimal orchestration receipt",
        "branch": 0
      },
      {
        "source": "Commit authoritative reporting",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
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
        "id": "validate-orchestration-envelope",
        "name": "Validate orchestration envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "require-explicit-customer-reference",
        "name": "Require explicit customer reference",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "require-explicit-customer-reference-accepted",
        "name": "Require explicit customer reference accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "require-explicit-customer-reference-review-required",
        "name": "Require explicit customer reference review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "resolve-requested-viewing-details",
        "name": "Resolve requested viewing details",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "require-explicit-booking-authorization",
        "name": "Require explicit booking authorization",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "require-explicit-booking-authorization-accepted",
        "name": "Require explicit booking authorization accepted",
        "type": "if",
        "position": [
          2630,
          220
        ]
      },
      {
        "id": "require-explicit-booking-authorization-review-required",
        "name": "Require explicit booking authorization review required",
        "type": "code",
        "position": [
          2630,
          410
        ]
      },
      {
        "id": "resolve-real-property",
        "name": "Resolve real property",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "require-currently-available-property",
        "name": "Require currently available property",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "require-currently-available-property-accepted",
        "name": "Require currently available property accepted",
        "type": "if",
        "position": [
          1330,
          770
        ]
      },
      {
        "id": "require-currently-available-property-review-required",
        "name": "Require currently available property review required",
        "type": "code",
        "position": [
          1330,
          960
        ]
      },
      {
        "id": "resolve-nominated-adviser",
        "name": "Resolve nominated adviser",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "require-active-adviser",
        "name": "Require active adviser",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "require-active-adviser-accepted",
        "name": "Require active adviser accepted",
        "type": "if",
        "position": [
          2630,
          770
        ]
      },
      {
        "id": "require-active-adviser-review-required",
        "name": "Require active adviser review required",
        "type": "code",
        "position": [
          2630,
          960
        ]
      },
      {
        "id": "validate-customer-booking-binding",
        "name": "Validate customer booking binding",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "validate-customer-booking-binding-accepted",
        "name": "Validate customer booking binding accepted",
        "type": "if",
        "position": [
          3280,
          770
        ]
      },
      {
        "id": "validate-customer-booking-binding-review-required",
        "name": "Validate customer booking binding review required",
        "type": "code",
        "position": [
          3280,
          960
        ]
      },
      {
        "id": "normalize-timezone-aware-start",
        "name": "Normalize timezone-aware start",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "require-future-timezone-aware-slot",
        "name": "Require future timezone-aware slot",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "require-future-timezone-aware-slot-accepted",
        "name": "Require future timezone-aware slot accepted",
        "type": "if",
        "position": [
          1980,
          1320
        ]
      },
      {
        "id": "require-future-timezone-aware-slot-review-required",
        "name": "Require future timezone-aware slot review required",
        "type": "code",
        "position": [
          1980,
          1510
        ]
      },
      {
        "id": "calculate-reservation-duration",
        "name": "Calculate reservation duration",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "find-customer-schedule-conflicts",
        "name": "Find customer schedule conflicts",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "find-adviser-schedule-conflicts",
        "name": "Find adviser schedule conflicts",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "find-property-schedule-conflicts",
        "name": "Find property schedule conflicts",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "prepare-company-hours-verification",
        "name": "Prepare company-hours verification",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "prepare-consent-aware-reminder-plan",
        "name": "Prepare consent-aware reminder plan",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "commit-authoritative-appointment",
        "name": "Commit authoritative appointment",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "return-minimal-orchestration-receipt",
        "name": "Return minimal orchestration receipt",
        "type": "code",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Validate orchestration envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Require explicit customer reference",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Require explicit customer reference",
        "target": "Require explicit customer reference accepted",
        "branch": 0
      },
      {
        "source": "Require explicit customer reference accepted",
        "target": "Resolve requested viewing details",
        "branch": 0
      },
      {
        "source": "Require explicit customer reference accepted",
        "target": "Require explicit customer reference review required",
        "branch": 1
      },
      {
        "source": "Require explicit customer reference review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Resolve requested viewing details",
        "target": "Require explicit booking authorization",
        "branch": 0
      },
      {
        "source": "Require explicit booking authorization",
        "target": "Require explicit booking authorization accepted",
        "branch": 0
      },
      {
        "source": "Require explicit booking authorization accepted",
        "target": "Resolve real property",
        "branch": 0
      },
      {
        "source": "Require explicit booking authorization accepted",
        "target": "Require explicit booking authorization review required",
        "branch": 1
      },
      {
        "source": "Require explicit booking authorization review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Resolve real property",
        "target": "Require currently available property",
        "branch": 0
      },
      {
        "source": "Require currently available property",
        "target": "Require currently available property accepted",
        "branch": 0
      },
      {
        "source": "Require currently available property accepted",
        "target": "Resolve nominated adviser",
        "branch": 0
      },
      {
        "source": "Require currently available property accepted",
        "target": "Require currently available property review required",
        "branch": 1
      },
      {
        "source": "Require currently available property review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Resolve nominated adviser",
        "target": "Require active adviser",
        "branch": 0
      },
      {
        "source": "Require active adviser",
        "target": "Require active adviser accepted",
        "branch": 0
      },
      {
        "source": "Require active adviser accepted",
        "target": "Validate customer booking binding",
        "branch": 0
      },
      {
        "source": "Require active adviser accepted",
        "target": "Require active adviser review required",
        "branch": 1
      },
      {
        "source": "Require active adviser review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate customer booking binding",
        "target": "Validate customer booking binding accepted",
        "branch": 0
      },
      {
        "source": "Validate customer booking binding accepted",
        "target": "Normalize timezone-aware start",
        "branch": 0
      },
      {
        "source": "Validate customer booking binding accepted",
        "target": "Validate customer booking binding review required",
        "branch": 1
      },
      {
        "source": "Validate customer booking binding review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Normalize timezone-aware start",
        "target": "Require future timezone-aware slot",
        "branch": 0
      },
      {
        "source": "Require future timezone-aware slot",
        "target": "Require future timezone-aware slot accepted",
        "branch": 0
      },
      {
        "source": "Require future timezone-aware slot accepted",
        "target": "Calculate reservation duration",
        "branch": 0
      },
      {
        "source": "Require future timezone-aware slot accepted",
        "target": "Require future timezone-aware slot review required",
        "branch": 1
      },
      {
        "source": "Require future timezone-aware slot review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Calculate reservation duration",
        "target": "Find customer schedule conflicts",
        "branch": 0
      },
      {
        "source": "Find customer schedule conflicts",
        "target": "Find adviser schedule conflicts",
        "branch": 0
      },
      {
        "source": "Find adviser schedule conflicts",
        "target": "Find property schedule conflicts",
        "branch": 0
      },
      {
        "source": "Find property schedule conflicts",
        "target": "Prepare company-hours verification",
        "branch": 0
      },
      {
        "source": "Prepare company-hours verification",
        "target": "Prepare consent-aware reminder plan",
        "branch": 0
      },
      {
        "source": "Prepare consent-aware reminder plan",
        "target": "Commit authoritative appointment",
        "branch": 0
      },
      {
        "source": "Commit authoritative appointment",
        "target": "Return minimal orchestration receipt",
        "branch": 0
      },
      {
        "source": "Commit authoritative appointment",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
    ]
  },
  {
    "name": "MADAR WhatsApp Conversation",
    "key": "madar-whatsapp-conversation",
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
        "id": "validate-orchestration-envelope",
        "name": "Validate orchestration envelope",
        "type": "code",
        "position": [
          420,
          220
        ]
      },
      {
        "id": "read-tenant-scoped-business-context",
        "name": "Read tenant-scoped business context",
        "type": "httpRequest",
        "position": [
          710,
          220
        ]
      },
      {
        "id": "require-customer-conversation",
        "name": "Require customer conversation",
        "type": "code",
        "position": [
          1060,
          220
        ]
      },
      {
        "id": "require-customer-conversation-accepted",
        "name": "Require customer conversation accepted",
        "type": "if",
        "position": [
          1330,
          220
        ]
      },
      {
        "id": "require-customer-conversation-review-required",
        "name": "Require customer conversation review required",
        "type": "code",
        "position": [
          1330,
          410
        ]
      },
      {
        "id": "validate-conversation-history-envelope",
        "name": "Validate conversation history envelope",
        "type": "code",
        "position": [
          1710,
          220
        ]
      },
      {
        "id": "validate-conversation-history-envelope-accepted",
        "name": "Validate conversation history envelope accepted",
        "type": "if",
        "position": [
          1980,
          220
        ]
      },
      {
        "id": "validate-conversation-history-envelope-review-required",
        "name": "Validate conversation history envelope review required",
        "type": "code",
        "position": [
          1980,
          410
        ]
      },
      {
        "id": "resolve-recent-inbound-context",
        "name": "Resolve recent inbound context",
        "type": "code",
        "position": [
          2360,
          220
        ]
      },
      {
        "id": "detect-customer-conversation-language",
        "name": "Detect customer conversation language",
        "type": "code",
        "position": [
          3010,
          220
        ]
      },
      {
        "id": "locate-latest-inbound-timestamp",
        "name": "Locate latest inbound timestamp",
        "type": "code",
        "position": [
          1060,
          770
        ]
      },
      {
        "id": "evaluate-meta-service-window",
        "name": "Evaluate Meta service window",
        "type": "code",
        "position": [
          1710,
          770
        ]
      },
      {
        "id": "identify-customer-opt-out-boundary",
        "name": "Identify customer opt-out boundary",
        "type": "code",
        "position": [
          2360,
          770
        ]
      },
      {
        "id": "identify-proactive-consent-boundary",
        "name": "Identify proactive consent boundary",
        "type": "code",
        "position": [
          3010,
          770
        ]
      },
      {
        "id": "identify-human-ownership-boundary",
        "name": "Identify human ownership boundary",
        "type": "code",
        "position": [
          1060,
          1320
        ]
      },
      {
        "id": "select-permitted-response-class",
        "name": "Select permitted response class",
        "type": "code",
        "position": [
          1710,
          1320
        ]
      },
      {
        "id": "validate-listing-grounding",
        "name": "Validate listing grounding",
        "type": "code",
        "position": [
          2360,
          1320
        ]
      },
      {
        "id": "validate-listing-grounding-accepted",
        "name": "Validate listing grounding accepted",
        "type": "if",
        "position": [
          2630,
          1320
        ]
      },
      {
        "id": "validate-listing-grounding-review-required",
        "name": "Validate listing grounding review required",
        "type": "code",
        "position": [
          2630,
          1510
        ]
      },
      {
        "id": "validate-message-length-boundary",
        "name": "Validate message length boundary",
        "type": "code",
        "position": [
          3010,
          1320
        ]
      },
      {
        "id": "validate-message-length-boundary-accepted",
        "name": "Validate message length boundary accepted",
        "type": "if",
        "position": [
          3280,
          1320
        ]
      },
      {
        "id": "validate-message-length-boundary-review-required",
        "name": "Validate message length boundary review required",
        "type": "code",
        "position": [
          3280,
          1510
        ]
      },
      {
        "id": "validate-source-channel-policy",
        "name": "Validate source channel policy",
        "type": "code",
        "position": [
          1060,
          1870
        ]
      },
      {
        "id": "validate-source-channel-policy-accepted",
        "name": "Validate source channel policy accepted",
        "type": "if",
        "position": [
          1330,
          1870
        ]
      },
      {
        "id": "validate-source-channel-policy-review-required",
        "name": "Validate source channel policy review required",
        "type": "code",
        "position": [
          1330,
          2060
        ]
      },
      {
        "id": "require-recorded-consent-representation",
        "name": "Require recorded consent representation",
        "type": "code",
        "position": [
          1710,
          1870
        ]
      },
      {
        "id": "require-recorded-consent-representation-accepted",
        "name": "Require recorded consent representation accepted",
        "type": "if",
        "position": [
          1980,
          1870
        ]
      },
      {
        "id": "require-recorded-consent-representation-review-required",
        "name": "Require recorded consent representation review required",
        "type": "code",
        "position": [
          1980,
          2060
        ]
      },
      {
        "id": "prepare-agent-review-context",
        "name": "Prepare agent review context",
        "type": "code",
        "position": [
          2360,
          1870
        ]
      },
      {
        "id": "prepare-approval-only-draft-contract",
        "name": "Prepare approval-only draft contract",
        "type": "code",
        "position": [
          3010,
          1870
        ]
      },
      {
        "id": "commit-authoritative-conversation",
        "name": "Commit authoritative conversation",
        "type": "httpRequest",
        "position": [
          3820,
          1870
        ]
      },
      {
        "id": "redact-backend-rejection",
        "name": "Redact backend rejection",
        "type": "code",
        "position": [
          3820,
          2170
        ]
      },
      {
        "id": "record-scoped-failure-incident",
        "name": "Record scoped failure incident",
        "type": "httpRequest",
        "position": [
          4130,
          2350
        ]
      },
      {
        "id": "stop-rejected-business-execution",
        "name": "Stop rejected business execution",
        "type": "code",
        "position": [
          4440,
          2350
        ]
      },
      {
        "id": "return-minimal-orchestration-receipt",
        "name": "Return minimal orchestration receipt",
        "type": "code",
        "position": [
          4100,
          1870
        ]
      },
      {
        "id": "input-and-authority",
        "name": "INPUT AND AUTHORITY",
        "type": "stickyNote",
        "position": [
          1010,
          130
        ],
        "note": "## INPUT AND AUTHORITY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "qualification-and-policy",
        "name": "QUALIFICATION AND POLICY",
        "type": "stickyNote",
        "position": [
          1010,
          680
        ],
        "note": "## QUALIFICATION AND POLICY\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "business-decisions",
        "name": "BUSINESS DECISIONS",
        "type": "stickyNote",
        "position": [
          1010,
          1230
        ],
        "note": "## BUSINESS DECISIONS\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      },
      {
        "id": "evidence-and-commit",
        "name": "EVIDENCE AND COMMIT",
        "type": "stickyNote",
        "position": [
          1010,
          1780
        ],
        "note": "## EVIDENCE AND COMMIT\nDistinct evidence calculations and connected validation branches. Mutations commit atomically; failures use the bound Error Monitor.",
        "width": 2600,
        "height": 450
      }
    ],
    "edges": [
      {
        "source": "Called by workflow",
        "target": "Validate orchestration envelope",
        "branch": 0
      },
      {
        "source": "Validate orchestration envelope",
        "target": "Read tenant-scoped business context",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Require customer conversation",
        "branch": 0
      },
      {
        "source": "Read tenant-scoped business context",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Require customer conversation",
        "target": "Require customer conversation accepted",
        "branch": 0
      },
      {
        "source": "Require customer conversation accepted",
        "target": "Validate conversation history envelope",
        "branch": 0
      },
      {
        "source": "Require customer conversation accepted",
        "target": "Require customer conversation review required",
        "branch": 1
      },
      {
        "source": "Require customer conversation review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate conversation history envelope",
        "target": "Validate conversation history envelope accepted",
        "branch": 0
      },
      {
        "source": "Validate conversation history envelope accepted",
        "target": "Resolve recent inbound context",
        "branch": 0
      },
      {
        "source": "Validate conversation history envelope accepted",
        "target": "Validate conversation history envelope review required",
        "branch": 1
      },
      {
        "source": "Validate conversation history envelope review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Resolve recent inbound context",
        "target": "Detect customer conversation language",
        "branch": 0
      },
      {
        "source": "Detect customer conversation language",
        "target": "Locate latest inbound timestamp",
        "branch": 0
      },
      {
        "source": "Locate latest inbound timestamp",
        "target": "Evaluate Meta service window",
        "branch": 0
      },
      {
        "source": "Evaluate Meta service window",
        "target": "Identify customer opt-out boundary",
        "branch": 0
      },
      {
        "source": "Identify customer opt-out boundary",
        "target": "Identify proactive consent boundary",
        "branch": 0
      },
      {
        "source": "Identify proactive consent boundary",
        "target": "Identify human ownership boundary",
        "branch": 0
      },
      {
        "source": "Identify human ownership boundary",
        "target": "Select permitted response class",
        "branch": 0
      },
      {
        "source": "Select permitted response class",
        "target": "Validate listing grounding",
        "branch": 0
      },
      {
        "source": "Validate listing grounding",
        "target": "Validate listing grounding accepted",
        "branch": 0
      },
      {
        "source": "Validate listing grounding accepted",
        "target": "Validate message length boundary",
        "branch": 0
      },
      {
        "source": "Validate listing grounding accepted",
        "target": "Validate listing grounding review required",
        "branch": 1
      },
      {
        "source": "Validate listing grounding review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate message length boundary",
        "target": "Validate message length boundary accepted",
        "branch": 0
      },
      {
        "source": "Validate message length boundary accepted",
        "target": "Validate source channel policy",
        "branch": 0
      },
      {
        "source": "Validate message length boundary accepted",
        "target": "Validate message length boundary review required",
        "branch": 1
      },
      {
        "source": "Validate message length boundary review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Validate source channel policy",
        "target": "Validate source channel policy accepted",
        "branch": 0
      },
      {
        "source": "Validate source channel policy accepted",
        "target": "Require recorded consent representation",
        "branch": 0
      },
      {
        "source": "Validate source channel policy accepted",
        "target": "Validate source channel policy review required",
        "branch": 1
      },
      {
        "source": "Validate source channel policy review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Require recorded consent representation",
        "target": "Require recorded consent representation accepted",
        "branch": 0
      },
      {
        "source": "Require recorded consent representation accepted",
        "target": "Prepare agent review context",
        "branch": 0
      },
      {
        "source": "Require recorded consent representation accepted",
        "target": "Require recorded consent representation review required",
        "branch": 1
      },
      {
        "source": "Require recorded consent representation review required",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Prepare agent review context",
        "target": "Prepare approval-only draft contract",
        "branch": 0
      },
      {
        "source": "Prepare approval-only draft contract",
        "target": "Commit authoritative conversation",
        "branch": 0
      },
      {
        "source": "Commit authoritative conversation",
        "target": "Return minimal orchestration receipt",
        "branch": 0
      },
      {
        "source": "Commit authoritative conversation",
        "target": "Redact backend rejection",
        "branch": 1
      },
      {
        "source": "Redact backend rejection",
        "target": "Record scoped failure incident",
        "branch": 0
      },
      {
        "source": "Record scoped failure incident",
        "target": "Stop rejected business execution",
        "branch": 0
      }
    ],
    "active": false,
    "contracts": [
      "/api/bridge/enterprise/context",
      "/api/bridge/enterprise/commit",
      "/api/bridge/enterprise/failure"
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
