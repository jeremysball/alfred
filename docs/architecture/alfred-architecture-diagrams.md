# Alfred Architecture Diagrams

## 1. System context

```mermaid
flowchart TB
    user[User]

    subgraph interfaces[User-facing interfaces]
        tui[TUI / CLI<br>Current]
        webui[Web UI<br>Current]
        telegram[Telegram<br>Current, less central]
        croncli[Cron CLI / job management<br>Current]
    end

    subgraph runtime[Alfred runtime]
        core[Alfred core runtime<br>Current]
        context[Context assembly<br>Current]
        prompts[Managed prompt files<br>Current<br>SYSTEM.md / AGENTS.md / SOUL.md / USER.md]
        tools[Tool execution<br>Current]
        llm[LLM provider orchestration<br>Current]
        memory[Memory + support state<br>Current foundation]
        support[Relational support runtime<br>Current foundation + planned expansion]
        selfmodel[Runtime self-model / inspection<br>Current]
    end

    subgraph storage[Persistence and retrieval]
        sqlite[(SQLite store<br>Current primary store)]
        curated[Curated memory<br>Current]
        archive[Session archive + tool provenance<br>Current]
        supportmem[Support memory state<br>Current foundation]
        embeddings[Embeddings provider<br>Current]
    end

    subgraph externals[External and local integrations]
        provider[Chat model providers<br>Current: Kimi<br>Planned: multi-provider]
        embedprov[Embedding providers<br>Current: OpenAI / local BGE]
        jobs[Background cron execution<br>Current]
    end

    user --> tui
    user --> webui
    user --> telegram
    user --> croncli

    tui --> core
    webui --> core
    telegram --> core
    croncli --> core

    core --> context
    context --> prompts
    core --> tools
    core --> llm
    core --> memory
    core --> support
    core --> selfmodel

    memory --> curated
    memory --> archive
    memory --> supportmem
    curated --> sqlite
    archive --> sqlite
    supportmem --> sqlite
    embeddings --> sqlite

    llm --> provider
    embeddings --> embedprov
    jobs --> sqlite
    jobs --> core
```

## 2. Current runtime container view

```mermaid
flowchart LR
    subgraph interfaces[Interfaces]
        cli[TUI / CLI]
        web[Web UI]
        tg[Telegram]
        cron[Cron daemon / cron commands]
    end

    subgraph app[Application runtime]
        config[Config loading<br>alfred.config]
        core[Core orchestration<br>Current]
        session[Session management<br>Current]
        ctx[ContextLoader / context assembly<br>Current]
        template[TemplateManager / sync<br>Current]
        tools[Tool registry + execution<br>Current]
        stream[Streaming response loop<br>Current]
        inspect["/context + self-model surfaces<br>Current"]
    end

    subgraph intelligence[Intelligence services]
        chat[LLMFactory / provider chat + stream<br>Current]
        embed[Embedding provider<br>Current]
        policy[Support policy compiler<br>Current foundation]
        adjudication[Semantic adjudication<br>Planned]
    end

    subgraph data[Data services]
        sqlite[(SQLite)]
        cur[Curated memory]
        sess[Session archive]
        sup[Support memory / profile / episodes]
        crondata[Cron data]
    end

    cli --> core
    web --> core
    tg --> core
    cron --> core

    config --> core
    core --> session
    core --> ctx
    core --> template
    core --> tools
    core --> stream
    core --> inspect

    ctx --> chat
    ctx --> cur
    ctx --> sess
    ctx --> sup
    core --> policy
    policy -. planned richer judgments .-> adjudication
    chat --> sqlite
    embed --> sqlite

    cur --> sqlite
    sess --> sqlite
    sup --> sqlite
    crondata --> sqlite
```

## 3. Current turn flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant I as Interface
    participant C as Core runtime
    participant X as Context loader
    participant M as Memory/support retrieval
    participant P as Support policy compiler
    participant L as LLM provider
    participant T as Tool executor
    participant S as SQLite store

    U->>I: Send message / command
    I->>C: Normalized request
    C->>X: Assemble context
    X->>S: Load managed files state / sync info
    X->>M: Fetch relevant memory + support state
    M->>S: Query curated memory, session archive, support data
    M-->>X: Retrieved context inputs
    X-->>C: Assembled prompt context

    C->>P: Resolve support behavior contract
    P->>S: Load scoped support/relational values
    P-->>C: Behavior contract

    C->>L: Start streaming chat
    alt Tool call requested
        L-->>C: Tool call
        C->>T: Execute tool
        T->>S: Persist tool outcomes if needed
        T-->>C: Tool result
        C->>L: Continue with tool result
    end
    L-->>C: Stream response chunks
    C->>S: Persist session messages + tool provenance
    C-->>I: Stream output
    I-->>U: Visible response
```

## 4. Current memory and continuity architecture

```mermaid
flowchart TB
    subgraph alwayson[Always-loaded durable context]
        system[SYSTEM.md]
        agents[AGENTS.md]
        soul[SOUL.md]
        usermd[USER.md]
    end

    subgraph memorylayers[Memory layers]
        curated[Curated memory<br>Current]
        archive[Session archive<br>Current]
        episodes[Support episodes + evidence refs<br>Current]
        operational[Life domains / operational arcs / work state<br>Current]
        situations[ArcSituation / GlobalSituation<br>Current]
        profile[Support profile values<br>Current]
        patterns[Patterns / review state<br>Current foundation, expanding]
    end

    subgraph retrieval[Runtime retrieval order]
        currentturn[Current conversation]
        supportfirst[Operational-first retrieval seam<br>Current]
        inject[Auto-injected curated memory<br>Current]
        fallback[Archive fallback / provenance search<br>Current]
    end

    currentturn --> alwayson
    alwayson --> supportfirst
    supportfirst --> operational
    operational --> situations
    supportfirst --> episodes
    supportfirst --> profile
    supportfirst --> patterns
    supportfirst --> inject
    inject --> curated
    supportfirst --> fallback
    fallback --> archive
```

## 5. Current support runtime vs planned support runtime

```mermaid
flowchart TB
    subgraph current[Current support runtime foundation]
        assess[Need / response-mode assessment<br>Current heuristic foundation]
        resolve[Resolve support + relational values<br>Current]
        compile[Compile behavior contract<br>Current]
        intervene[Choose intervention family<br>Current]
        attempt[Record support attempt<br>Current]
        inspect[Inspection and review surfaces<br>Current foundation]
    end

    subgraph planned[Planned richer support runtime]
        semantic[Semantic adjudication over symbolic state<br>Planned]
        caselrn[Case-based learning v2<br>Planned]
        stance[Semantic relational-state + stance adjudication<br>Planned]
        extraction[Natural-language observation extraction<br>Planned]
        surfacing[Pattern + relational surfacing adjudication<br>Planned]
    end

    assess --> resolve --> compile --> intervene --> attempt --> inspect

    semantic -. replaces heuristic seams .-> assess
    semantic -. enriches subject / need / session routing .-> resolve
    caselrn -. updates learned values and cases .-> resolve
    stance -. applies bounded stance deltas .-> compile
    extraction -. produces typed observations .-> caselrn
    surfacing -. controls when to explain or surface .-> inspect
```

## 6. Planned learning and evidence architecture

```mermaid
flowchart LR
    transcript[Transcript sessions + message refs<br>Current raw archive]
    toolprov[Tool provenance<br>Current]
    feedback[User corrections / feedback / support controls<br>Current foundation]
    transitions[Operational transitions<br>Current foundation]

    subgraph substrate[Generalized semantic substrate]
        traces[Interaction / runtime traces<br>Current + planned generalization]
        observations[Grounded observations<br>Planned generalized substrate]
        updates[Deterministic state updates / learned-state candidates<br>Planned generalized substrate]
    end

    subgraph models[Projected ontologies]
        operational[Operational projection<br>Current foundation + planned richer patterns]
        relational[Relational projection<br>Current foundation + planned richer stance semantics]
        future[Future projections<br>Open-ended]
        handles[Cross-domain handles / ownership / dedupe<br>Planned]
    end

    subgraph outputs[User-visible and runtime outputs]
        values[Scoped projection values / projected state<br>Current]
        review[Review cards / inspection / correction<br>Current foundation + planned expansion]
        runtime[Effective runtime contract<br>Current]
    end

    transcript --> traces
    toolprov --> traces
    feedback --> observations
    transitions --> observations
    traces --> updates
    observations --> updates

    updates --> operational
    updates --> relational
    updates --> future
    operational -. planned shared identity layer .-> handles
    relational -. planned shared identity layer .-> handles
    future -. planned shared identity layer .-> handles

    operational --> values
    relational --> values
    future --> values
    values --> runtime
    handles --> review
    operational --> review
    relational --> review
    future --> review
```

## 7. Current storage architecture

```mermaid
flowchart TB
    subgraph producers[Writers]
        runtime[Runtime conversation loop]
        tools[Tools]
        cron[Cron system]
        memoryops[Memory/support updaters]
    end

    subgraph store[Unified persistence]
        sqlite[(SQLite store<br>Current source of truth)]
    end

    subgraph logical[Logical datasets]
        sessions[Sessions + messages]
        toolcalls[Tool calls / provenance]
        curated[Curated memory]
        support[Support memory objects<br>Episodes / arcs / domains / profile values]
        cronjobs[Cron jobs + history]
        vectors[Embeddings / vector search backing]
    end

    runtime --> sqlite
    tools --> sqlite
    cron --> sqlite
    memoryops --> sqlite

    sqlite --> sessions
    sqlite --> toolcalls
    sqlite --> curated
    sqlite --> support
    sqlite --> cronjobs
    sqlite --> vectors
```

## 8. Interface and transport view

```mermaid
flowchart LR
    subgraph local[Local-first surfaces]
        tui[TUI / CLI<br>Current]
        web[Web UI<br>Current]
        cronui[Cron commands<br>Current]
    end

    subgraph optional[Optional / secondary surfaces]
        tg[Telegram<br>Current, secondary]
    end

    subgraph services[Runtime services]
        app[Shared Alfred runtime]
        ws[WebSocket / live UI state<br>Current foundation, improving]
        notifications[Notification paths<br>Current foundation]
    end

    tui --> app
    web --> ws
    ws --> app
    cronui --> app
    tg --> app
    app --> notifications
```

## 9. Planned architecture trajectory map

```mermaid
flowchart TD
    past[Memory-augmented assistant<br>Past center of gravity]
    current[Local-first assistant with support-memory foundation<br>Current]
    next1[Relational support runtime with bounded policy compiler<br>Current + in progress]
    next2[Semantic adjudication over symbolic runtime state<br>Planned]
    next3[Case-based learning, richer inspection, and cross-domain coordination<br>Planned]
    target[Persistent relational support system with operational intelligence<br>Target]

    past --> current --> next1 --> next2 --> next3 --> target
```

## 10. Ownership map

```mermaid
flowchart TB
    subgraph markdown[Managed markdown truth]
        sys[SYSTEM.md<br>Owns support operating model / retrieval order / promotion rules]
        ag[AGENTS.md<br>Owns execution and tool behavior rules]
        so[SOUL.md<br>Owns Alfred identity / voice / relational posture]
        us[USER.md<br>Owns explicit user-confirmed durable truths]
    end

    subgraph runtime[Structured runtime truth]
        supportstate[Support memory<br>Owns active operational continuity]
        profile[Support learning / profile state<br>Owns effective support and relational adaptation]
        curated[Curated memory<br>Owns reusable remembered facts]
        archive[Session archive<br>Owns raw provenance and recall]
    end

    sys --> supportstate
    ag --> supportstate
    so --> profile
    us --> curated
    archive --> supportstate
    archive --> profile
```
