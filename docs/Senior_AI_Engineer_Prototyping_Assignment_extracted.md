# 🧠 Prototyping Assignment
## AI-Powered RFQ → Vendor Evaluation → Award Decision System

---

## ⚠️ Important Note
This should be a working AI prototype.

- No static dashboards
- No hardcoded outputs
- AI must actively process inputs and generate results

---

## 🎯 Goal (in simple terms)
Build a working system that:

- Takes an RFQ
- Sends structured + AI-generated questionnaires to vendors
- Accepts messy vendor quotation documents
- Extracts and compares them
- Helps a buyer decide who to award and why

---

## 🧩 Why This Assignment Exists

In real procurement workflows, especially for categories like marketing services, the process looks like this:

- A buyer creates an RFQ with scope, timelines, and line items
- Multiple vendors respond, but not in a standard format
- Each vendor sends their own style of documents (PPTs, PDFs, Excel sheets)
- Information is scattered, inconsistent, and often incomplete
- The buyer spends hours manually:
  - reading documents
  - comparing quotes
  - aligning scope
  - making trade-offs

👉 This process is slow, error-prone, and hard to scale

---

## 🤖 Where AI Comes In

AI can help:

- structure unstructured documents
- extract and normalize key data
- highlight differences and risks
- support better, faster decision-making

But in reality:

- It’s not just about generating text
- It’s about building a reliable system that works end-to-end

---

## 🧠 How This Relates to the Role

As a Senior Applied AI Engineer, your day-to-day work will involve:

- Taking ambiguous, real-world problems like this
- Designing AI-powered systems end-to-end
- Deciding:
  - where to use AI
  - where to use rules
  - how to make outputs reliable
- Building fast prototypes that can evolve into product features
- Working closely with product and business teams to deliver real value

👉 This assignment simulates that exact responsibility

---

## 🎯 What We Want to See

We are not just looking for:

- a UI, or a single AI prompt

We are looking for:

- how you think about the problem
- how you structure the system
- how you make outputs useful and trustworthy
- how you balance simplicity and effectiveness

---

## 💬 One Important Note

If anything is unclear, please reach out. We prefer thoughtful questions over incorrect assumptions.

---

## 🧩 End-to-End Flow (what you need to build)

### Page 1: Step A : RFQ + Questionnaire Generation

A sample RFQ has these components:

- General Information Section
- Timelines
- Item Requests
- Scope of Work
- Questionnaire

Your system should:

1. Read the other RFQ component’s data (scope, line items, timelines, etc.)
2. Have a button that triggers an AI agent to generate vendor questionnaires  
   (There can be multiple types of questionnaires)

Show the questionnaire section on the UI.

**Example**

If RFQ says:

“TVC production with child safety compliance”

Your system may generate:

- What is your experience with child talent compliance?
- Share 3 relevant past campaigns
- What safety processes do you follow?

---

### Page 2: Step B : Vendor Responses (Messy Documents)

Assume:

- RFQ is sent to 5 vendors
- Each vendor uploads 1 document (any format)

Supported formats:

- PDF
- PPT
- Excel
- Word

👉 Build a simple upload page

⚠️ Make documents realistically messy

Include at least 5 of these:

1. Pricing hidden in tables inside PDFs
2. Important info present as images in PPT
3. Vendors giving partial quotes (missing fields)
4. Very long documents (20–50 pages)
5. Different formats for same thing:
   - “Total Cost” vs “Grand Total” vs “Project Fee”
6. Mixed currencies or unclear units
7. Commercials split across multiple pages

---

### Page 3: Step C : Extraction + Normalization

Your system should:

1. Extract:
   - Pricing
   - Commercial terms
   - Scope coverage
   - Delivery timelines
   - Key terms

2. Normalize:
   - Convert everything into same structure
   - Align line items with RFQ
   - Standardize naming

👉 This is a critical step: don’t skip structure

---

### Page 4: Step D : Technical Analysis Page

System should generate analysis:

- Which vendors meet requirements
- Where vendors differ
- Missing responses
- Strengths / weaknesses

👉 Must include evidence (from documents)

---

### Page 5: Step E : Commercial Comparison Dashboard

System should generate:

- Cost comparison
- Cost breakdown
- Anomalies (too high / too low)
- Missing pricing

---

### Page 6: Step F : Award Recommendation (MOST IMPORTANT)

Your system should:

1. Suggest:
   - Best vendor OR
   - Split award (e.g., Vendor A for production, Vendor B for media)

2. Run multiple scenarios:
   - Lowest cost
   - Fastest delivery
   - Best compliance

3. Explain:
   - Why this recommendation
   - Trade-offs
   - Confidence / risks

Important:

- Do NOT always pick lowest cost blindly
- SHOULD consider multiple factors (cost, compliance, scope, etc.)
- SHOULD allow trade-offs
- SHOULD explain reasoning clearly

---

## 🧪 What We Are Evaluating

1. End-to-End Thinking  
2. Product Thinking  
3. AI Usage (IMPORTANT)  
4. Handling Messy Data  
5. Explainability  
6. UX  
7. Grounded Outputs  

---

## 📦 Deliverables

**TIMEFRAME: 5 days**

1. Working Prototype:
   - Web app link
   - Runnable system
   - Sample vendor documents

2. Demo Video (5 mins):
   - System flow
   - Key decisions
   - Live demo

3. Transcript of Video

4. 1–2 Page Document:
   - Problem solved
   - Assumptions
   - System design
   - Key features
   - Improvements

5. Optional:
   - Architecture diagram
   - Evaluation approach
   - Logs / traces

---

## 💡 Guidance

Avoid:

- Dummy dashboards
- Easy vendor documents
- No evidence for outputs

Strong submissions show:

- Clear pipeline (extract → normalize → analyze → decide)
- Mix of AI + logic
- Grounded outputs
- Thoughtful UX
- Meaningful recommendations

---

## 🧠 Final Note

This assignment is intentionally open-ended.

There is no “one correct answer.”

We are evaluating:

👉 How you turn a messy real-world problem into a usable system
