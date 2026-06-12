# Design Specification: Panze Studio Dashboard

## 1. Overview
This document outlines the design system and layout specifications for the Panze Studio Project Dashboard. The design utilizes a modern, clean interface with a focus on data visualization and task management. It is built using Tailwind CSS utility classes.

---

## 2. Color Palette

### Base Colors
see basestyles.css for all colors


---

## 3. Typography
The dashboard utilizes the **Inter** font family for optimal legibility in analytical interfaces.

| Element | Size | Weight | Example Tailwind Class |
| :--- | :--- | :--- | :--- |
| Page Title | 30px (3xl) | Semibold (600) | `text-3xl font-semibold` |
| Section Header | 16px (base) | Semibold (600) | `font-semibold` |
| Body Text | 14px (sm) | Regular (400) / Medium (500) | `text-sm font-medium` |
| Small Labels | 12px (xs) | Medium (500) | `text-xs font-medium` |
| Micro Data | 10px / 11px | Regular (400) | `text-[11px]` |

---

## 4. Layout & Grid System

* **Overall Structure:** Full viewport height (`h-screen`) flex container.
* **Application Window:** Contained within a rounded window (`rounded-[2.5rem]`) with a white background and subtle shadow.
* **Sidebar:** Fixed width of `88px`. Flex column layout.
* **Main Content Area:** Flex column layout. Left/right padding of `32px` (`px-8`), vertical padding of `32px` (`py-8`).
* **Grid System:** The primary dashboard utilizes a 12-column grid (`grid-cols-12`) with a gap of `24px` (`gap-6`).
    * *My Tasks Column:* Spans 3 columns (`col-span-3`).
    * *Center Analytics Column:* Spans 6 columns (`col-span-6`).
    * *Right Sidebar Column:* Spans 3 columns (`col-span-3`).

---

## 5. UI Components

### 5.1 Cards
* **Border Radius:** `24px` (`rounded-3xl`) for main containers, `16px` (`rounded-2xl`) for internal items (like tasks or meetings).
* **Padding:** `20px` (`p-5`) or `24px` (`p-6`).
* **Styling:** White background (`bg-white`), light border (`border-gray-100`), small shadow (`shadow-sm`).

### 5.2 Buttons & Controls
* **Primary Action (Tabs):** Dark gray background (`bg-gray-900`), white text, fully rounded (`rounded-full`).
* **Secondary Action (Tabs):** Transparent background, gray text (`text-gray-600`), gray hover state (`hover:bg-gray-50`), fully rounded.
* **Icon Buttons:** `32px` x `32px` or `28px` x `28px`, circular (`rounded-full`), bordered (`border-gray-200`), hover state changes background to `bg-gray-50`.

### 5.3 Inputs
* **Search Bar:** Fully rounded (`rounded-full`), padded left for icon (`pl-10`), gray border. Focus state utilizes a ring (`focus:ring-gray-300`).

### 5.4 Iconography
* **Library:** Google Material Symbols Outlined.
* **Default Size:** `20px`.
* **Small Icons:** `16px` or `18px` specified via utility classes (e.g., `text-[16px]`).

---

## 6. Data Visualization Specifications

* **Donut Chart (Projects Overview):** Utilizes SVG with `stroke-dasharray` for segment rendering. Rotated -90 degrees to start from the top.
* **Line Chart (Income vs Expense):** Utilizes SVG. Contains a solid line with a semi-transparent filled area below for Income, and a dashed line with a semi-transparent filled area for Expense. Includes tooltip marker logic.
* **Horizontal Progress Bars (Invoice Overview):** Container height of `10px` (`h-2.5`), fully rounded corners. Fill percentage controlled via inline styles.