### AI-Centric Workload Distribution
This revision assigns one core AI/Prompting pipeline to each member. Frontend and backend tasks are attached directly to the member who built the underlying AI feature, eliminating API negotiation and reducing context switching.
| Member | Core AI Responsibility | Day 1 (Data & AI Pipelines) | Day 2 (UI & Integration) |
|---|---|---|---|
| **Member 1** | **Inbox Triage AI**
(Classification & Summarization) | **Phase 2:** Gmail OAuth login & fetch unread emails.
**Phase 3:** Classify / summarize / draft pipeline (JSON). | **Phase 4:** Store extracted Todos/Meetings in SQLite.
**Phase 8:** Email page UI (inbox list + AI draft view). |
| **Member 2** | **Commerce Data AI**
(Extraction & Structuring) | **Phase 5:** Order emails detected and structured data stored.
**Phase 6:** Analytics endpoint construction. | **Phase 10:** Orders page UI (status badges).
**Phase 7:** Home page UI (todos, meetings, live charts). |
| **Member 3** | **Generative AI**
(Content Creation & Tone) | **Phase 11:** Settings saved to DB, Gmail connect/disconnect.
**Phase 9:** Crafter pipeline (full email from tone + prompt). | **Phase 12:** n8n workflow runs end-to-end (pushes final Crafter draft to Gmail inbox). |
### Execution Strategy
 * **Day 1 Checkpoint:** By end of day, Member 1 must output valid JSON for triaged emails, Member 2 must output structured order data, and Member 3 must have a working text-generation prompt chain.
 * **Database Schema:** All members must finalize the SQLite schema for users, emails, orders, and todos in the first hour before diverging.
 * **Frontend Approach:** Since UI is low complexity, Members 1 and 2 build their respective views (Email, Orders, Home) on Day 2 using the exact JSON structures they finalized on Day 1. Member 3 focuses entirely on the n8n automation pipeline on Day 2 to guarantee end-to-end functionality.
