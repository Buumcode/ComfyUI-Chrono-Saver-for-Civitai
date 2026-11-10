# Civitai Metadata Research

The main goal was to make file with embedded ComfyUI workflow + injected Civitai AIR/resources metadata to auto-detection resources by Civitai.com.

But all todays code override COMFYUI engine:
1. AIR in `workflow.extra.airs` chunk - change COMFYUI engine to CIVITAI engine; 
2. Parameters chunk - change COMFYUI engine to External generator noname engine;
3. EXIF User comment chunk  - change COMFYUI engine to MADE ON-SITE engine; 

- every one "Civitai resources" variant override COMFYUI engine.

----
Investigation of Civitai's code gives result: private repo ORCHESTRATOR make work to convert metadata. 

```
┌───────────────────────────────────────────┐
│              civitai/civitai              │
│                                           │
│  createComfyInput()                       │
│                                           │
│  workflowData = {                         │
│      prompt,                              │
│      negativePrompt,                      │
│      steps,                               │
│      cfgScale,                            │
│      sampler,                             │
│      seed,                                │
│      workflowId,                          │
│      resources                            │
│  }                                        │
│                                           │
│  imageMetadata = JSON.stringify(...)      │
└──────────────────────┬────────────────────┘
                       │
                       ▼
             Civitai Orchestrator
             (PRIVATE repository)
                       │
                       │ imageMetadata
                       ▼
             ┌──────────────────┐
             │ metadata writer  │
             │                  │
             │ ???              │
             └────────┬─────────┘
                      │
                      ▼
                 PNG / WebP
                      │
             ┌────────┴────────┐
             │ metadata carrier│
             └────────┬────────┘
                      │
                      ▼
            Civitai image parser
                      │
                      ▼
              exif.extraMetadata
                      │
                      ▼
             comfy.metadata.ts
```
