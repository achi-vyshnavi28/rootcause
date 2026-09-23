# Process maps (as-is and to-be)

Mermaid diagrams render on GitHub. Swimlanes are shown as subgraphs.

## As-is: investigating a metric drop
```mermaid
flowchart LR
  subgraph Ops[Ops manager]
    A[Notices drop in dashboard] --> B[Raises ticket]
    J[Receives answer] --> K{Trust it?}
    K -- no --> B
    K -- yes --> L[Decides action]
  end
  subgraph Data[Data team]
    B --> C[Ticket waits in queue<br/>0.5-2 days]
    C --> D[Analyst writes 10-20 queries]
    D --> E{Cause found?}
    E -- no --> F[More slicing / ask engineers]
    F --> D
    E -- yes --> G[Writes Slack summary<br/>no audit trail]
  end
  G --> J
```
**Pain points:** queue time; repetitive slicing; data bugs discovered late; no reusable evidence; the same question asked again next month.

## To-be: with RootCause
```mermaid
flowchart LR
  subgraph Auto[RootCause]
    S[Daily anomaly scan] --> Q
    Q[Question] --> P[Plan metric + periods]
    P --> M[Measure all segments<br/>validated read-only SQL]
    M --> DQ{Data-quality issue?}
    DQ -- yes --> R1[Report: data bug<br/>+ cited incident docs]
    DQ -- no --> R2[Report: ranked causes,<br/>drill-down, confidence,<br/>next checks, experiment]
  end
  subgraph Ops[Ops manager]
    U[Asks why] --> Q
    R1 --> V{Confidence high?}
    R2 --> V
    V -- yes --> X[Acts / simulates fix]
    V -- low --> Y[Escalates with evidence]
  end
  subgraph Data[Data team]
    Y --> Z[Reviews audit trail,<br/>extends semantic layer]
  end
```
**Changes:** the queue is removed for routine cases; every answer carries its queries; data bugs are checked first; analysts handle only low-confidence cases, starting from the evidence rather than from scratch.
