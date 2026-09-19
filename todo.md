# ROLEX AI — Upgrade Plan (Voice Fix + Full Feature Build)

## 1. Voice Fix (CRITICAL — reported bug)
- [x] Rewrite `modules/voice.py` as a platform-aware facade
- [x] Add `modules/voice_android.py` — native TTS/STT via pyjnius
- [x] Add `modules/voice_desktop.py` — pyttsx3 + SpeechRecognition fallback
- [x] Wake words "Hey Rolex" / "Hey Guru" + amplitude for eye glow
- [x] Wire voice into GUI + app + buildozer permissions

## 2. Math Engine (offline, step-by-step)
- [x] Expand `modules/math_engine.py`: step-by-step solver, equation solver, formula library
- [x] `modules/math_solver.py` step-by-step (arithmetic/linear/quadratic/system/finance/stats)
- [x] `modules/formula_library.py` (~60 formulas)

## 3. Intelligence & Learning
- [x] `modules/self_learning.py` — daily learning routines
- [x] `modules/self_modify.py` + `modules/sandbox.py` — controlled self-modification, test, rollback
- [x] `modules/knowledge_graph.py` — knowledge graph
- [x] Enhance `modules/parallel_ai.py` — smart provider selection
- [x] Enhance `modules/memory.py` — short + long-term memory

## 4. Capability Modules
- [x] `modules/tool_manager.py` — tool manager
- [x] `modules/package_manager.py` — controlled package management
- [x] `modules/device.py` — device management
- [x] `modules/smarthome.py` — smart-home / IoT
- [x] `modules/messaging.py` — messaging/social + mail auto-answer
- [x] `modules/finance.py` — finance/business/travel/family
- [x] `modules/health.py` — health information support
- [x] `modules/biometrics.py` — fingerprint / face recognition
- [x] `modules/emergency.py` — emergency stop
- [x] `modules/remote_lab.py` — WebSocket architecture
- [x] `modules/coding.py` — coding/development capabilities
- [x] `modules/computer_knowledge.py` — computer knowledge
- [x] `modules/self_tests.py` — automated self-tests
- [x] `modules/recovery.py` — recovery / diagnostics
- [x] Enhance `modules/vision.py` — camera capture

## 5. Futuristic Autobots UI
- [x] Generate Optimus Prime hero image asset
- [x] `gui/optimus.py` — Optimus Prime widget with voice-synced glowing eyes
- [x] Rewrite `gui/rolex_gui.py` — Autobots theme, Optimus center, new screens
- [x] Expand `gui/theme.py`

## 6. Integration & Wiring
- [x] Wire all modules into `router.py` + `app.py`
- [x] Update `buildozer.spec`, `requirements.txt`, `.env.example`
- [x] Update README + docs

## 7. Verification & Delivery
- [x] Run tests / smoke checks (85 pytest pass, capability + router + GUI smoke pass, GUI renders verified)
- [ ] Push branch + open PR on GitHub
