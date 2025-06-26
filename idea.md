# Daily Taskification AI Agent Framework

*Optimising Google Analytics insights for Sales Teams*

---

## 1. Follow‑Up on Purchases (Cross‑Sell / Upsell)

### Objective

Increase average‑order value (AOV) and customer satisfaction by recommending complementary items.

### Google Analytics data

* Ecommerce purchase data
* Product SKU purchased
* Customer ID / email (via CRM)
* Time of purchase

### Enriched data required

* Product‑to‑product associations (PIM or internal mapping)
* Real‑time inventory availability

### Standard task for the sales rep

1. Identify customers who completed a purchase in the last **24–48 hours**.
2. Suggest 2‑3 related products that “complete the job.”
3. Offer a limited‑time discount if purchased within 48 hours.

#### Example task card

| Field                 | Value                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Customer**          | John Smith — [john.smith@email.com](mailto:john.smith@email.com) — +1 512‑757‑1877                           |
| **Company**           | *Company Name*                                                                                               |
| **Purchased item(s)** | Bosch Cordless Drill (SKU BOSCH123) — QTY 2 @ \$35.00                                                        |
| **Order date**        | 10 Jun 2025                                                                                                  |
| **Suggested items** (We shall do it later just have a place holder for this)  | • Bosch Drill Bit Set (BOSCHBITS001)<br>• Safety Goggles (SAFEGOG123)<br>• Battery Backup Pack (BOSCHBAT001) |
| **Inventory** (We shall do it later just have a place holder for this)         | All three items in stock                                                                                     |
| **Rep action**        | Call or email; offer discount valid 48 h                                                                     |
| **Goal**              | Raise AOV and ensure job completion                                                                          |

---

## 2. Reach Out to Cart Abandoners

### Objective

Recover abandoned carts and uncover user objections.

### Google Analytics data

* Cart‑abandonment reports
* Products added but not purchased
* User sessions mapped to CRM contact

### Task for the sales rep

1. Contact customers who abandoned high‑value or strategic items.
2. Offer assistance and, where appropriate, a time‑limited promotion.

#### Example task card

| Field               | Value                                                               |
| ------------------- | ------------------------------------------------------------------- |
| **Customer**        | Sarah Lopez — [sarah.lopez@email.com](mailto:sarah.lopez@email.com) |
| **Abandoned items** | Milwaukee Sawzall + Heavy‑Duty Blades                               |
| **Cart value**      | \$287.00                                                            |
| **Abandoned on**    | 10 Jun 2025 (14 min onsite)                                         |
| **Rep action**      | Call/email, offer 10 % off & answer questions                       |
| **Goal**            | Recover revenue and identify funnel friction                        |

---

## 3. Follow‑Up on Site Search with No Conversion

### Objective

Help high‑intent visitors who searched but did not buy.

### Google Analytics data

* On‑site search terms
* Product pages viewed / exit page
* Session duration; no purchase event

### Task for the sales rep

1. Identify users whose search indicated clear intent.
2. Clarify requirements, recommend alternatives, or arrange a custom order.

#### Example task card

| Field            | Value                                                         |
| ---------------- | ------------------------------------------------------------- |
| **Customer**     | Raj Patel — [raj.patel@email.com](mailto:raj.patel@email.com) |
| **Search term**  | “4‑inch copper pipe fittings”                                 |
| **Pages viewed** | 5 product pages (all out of stock)                            |
| **Exit page**    | “Product not available”                                       |
| **Rep action**   | Offer alternatives or source item                             |
| **Goal**         | Retain potential customer and enrich catalogue gaps           |

---

## 4. Follow‑Up on Repeat Visits Without Purchase

### Objective

Convert warm leads who revisit key pages.

### Google Analytics data

* Returning‑visitor report
* Repeated product/category views
* No checkout event

### Task for the sales rep

1. Reach out to repeat visitors on strategic SKUs.
2. Offer demos, spec sheets, or a call with technical support.

#### Example task card

| Field          | Value                                                          |
| -------------- | -------------------------------------------------------------- |
| **Customer**   | Maria Gonzalez — [maria.g@email.com](mailto:maria.g@email.com) |
| **Pattern**    | 3 visits in 5 days to Industrial Air Compressor (SKU AIR123)   |
| **Rep action** | Email demo invite & pricing assistance                         |
| **Goal**       | Close high‑interest prospect                                   |

---

### Task for the sales rep

1. Identify customers approaching the next reorder window.
2. Remind them and suggest bundled items.

#### Example task card

| Field                | Value                                                      |
| -------------------- | ---------------------------------------------------------- |
| **Customer**         | James Hall — [james.h@email.com](mailto:james.h@email.com) |
| **Last order**       | HVAC Air Filter (SKU HVAC001) on 10 Mar 2025               |
| **Expected reorder** | \~90 days                                                  |
| **Rep action**       | Reminder email + bundle suggestion                         |
| **Goal**             | Secure reorder before competitors do                       |

---

# Interface & UX Requirements

## Overview

Provide a web interface that organises the six action‑item categories above into tabbed views, each displaying user‑specific “task cards” with embedded task‑management controls.

## 1. Tabbed Navigation

* **Tabs**:

  * Purchases
  * Cart Abandoners
  * Site Search (No Conversion)
  * Repeat Visits
  * Performance / UX Issues
  * Re‑Orders
* Each tab label shows a live count of pending users.
* Switching tabs preserves unsaved notes or filters.
* Lazy‑load data per tab for performance.

## 2. Collapsible Task Card

**Collapsed view** shows:

* Company name
* User name
* Email / phone
* Date of last interaction
* Transaction or cart value

**Expanded view** adds:

* Action description
* Line‑item table (name, SKU, qty, price, image)
* Controls:

  * ✅ Task‑completed checkbox
  * 📝 Rich‑text notes field
  * 📅 Date‑time picker for follow‑up

*Behaviour*: When “Task Completed” is checked, the card greys out and auto‑collapses (user can reopen).

## 3. General UI/UX

* Fully responsive (desktop, tablet, mobile).
* Keyboard navigation & screen‑reader friendly; include high‑contrast mode.
* Smooth collapse/expand animation; distinctive icons per action type.
* Sticky tab headers for quick context while scrolling.

## 4. System Dashboard Email (Daily)

Morning email summary to reps:

* **Total tasks per category** (with deep‑link to the relevant tab).
* Optional high‑level KPIs: total visitors, repeat visitors, total purchases.

---

*End of cleaned Markdown document.*
