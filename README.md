# SalesVision Dashboard

🚀 **Live Dashboard:** [Open SalesVision Dashboard](https://salesvision-dashboard-ranaforge.streamlit.app)

Explore interactive e-commerce sales analytics, an India state sales map, and sales forecasts with honest uncertainty ranges.

## Project Overview

### Indian E-Commerce Sales Analysis & Sales Forecasting

SalesVision is an interactive data analytics dashboard built to explore an Indian e-commerce sales dataset, identify business patterns, visualize sales across Indian states, and show what a forecasting model can and cannot do with this data.

The project combines data analysis, interactive visualization, and a machine-learning workflow in a single Streamlit application.

> **Forecasting note:** The dataset covers **1 June 2024 through 30 June 2026**. The next-day forecast of **1 July 2026** is a historical, dataset-end prediction, not a forecast for today's sales.

------------------------------------------------------------------------

## Table of Contents

-   [Project Overview](#project-overview)
-   [Business Objectives](#business-objectives)
-   [Dashboard Features](#dashboard-features)
-   [Design Decisions](#design-decisions)
-   [Technology Stack](#technology-stack)
-   [Dataset](#dataset)
-   [Selected Findings](#selected-findings)
-   [Forecasting Approach](#forecasting-approach)
-   [Project Structure](#project-structure)
-   [Installation and Setup](#installation-and-setup)
-   [Run the Dashboard](#run-the-dashboard)
-   [How to Use](#how-to-use)
-   [Validation and Limitations](#validation-and-limitations)
-   [Future Improvements](#future-improvements)
-   [Author](#author)

------------------------------------------------------------------------

## Business Objectives

-   Analyze order volume, recorded order amounts, and order-status distribution.
-   Explore product-category, payment-mode, order-size, and state-level patterns.
-   Visualize geographic differences in sales across Indian states.
-   Show a next-day sales prediction together with the range it is likely to fall in.
-   Test the forecasting model against simple averages and report the result plainly.
-   Present the findings in a dashboard that can be explored by changing filters.

<!--
## Screenshots

Add screenshots to docs/screenshots/ and uncomment this section:

| Overview | Sales Analysis |
|---|---|
| ![Overview](docs/screenshots/overview.png) | ![Sales Analysis](docs/screenshots/sales-analysis.png) |

| India Sales Map | Forecasting |
|---|---|
| ![India Sales Map](docs/screenshots/india-sales-map.png) | ![Forecasting](docs/screenshots/forecasting.png) |
-->

## Dashboard Features

### Shared filters

The sidebar has a quick-range control (7D, 30D, 90D, 1Y, All), a calendar popup for custom date ranges, and a state selector with Select all and Clear. The Overview, Sales Analysis and India Sales Map pages respond to these filters. **The Forecasting page ignores them** (see [Design Decisions](#design-decisions)) and says so when filters are active.

### 1. Overview

A one-screen summary of delivered sales.

-   Four KPI cards: delivered sales, total orders, average order value and return rate. Each shows a weekly sparkline and the change against the previous period of equal length (when earlier data exists).
-   A sales trend with a Daily, Weekly or Monthly view, a moving average and an average line. The choices adapt to the selected range (for example, a 7-day range offers only Daily). Part-weeks and part-months at the edges are drawn lighter and left out of the average.
-   A one-line takeaway about how steady sales are.
-   Order outcomes (delivered, shipped, processing, returned, cancelled), sales by category, and top states.

### 2. Sales Analysis

A deeper look at what sells and how customers buy. A **Delivered / All orders** switch controls every number on the page, and Delivered is the default so totals agree with the Overview.

-   KPI cards for sales, orders, average order and **median order**, with changes against the previous period.
-   Sales by category with the average order size of each category.
-   Top products and top brands.
-   Order-size bands, comparing the share of orders with the share of sales.
-   Payment modes (share of orders against share of sales) with coupon usage and cost.
-   Sales by state, delivery time, and a check on whether any state stands out for returns or cancellations.
-   A table of the orders behind the numbers.

### 3. India Sales Map

A state-level map built from a simplified GeoJSON file.

-   Colour by delivered sales, delivered orders or average order. States with no delivered orders in the current filter are grey, so they are never mistaken for low values.
-   A ranked list beside the map, so small states such as Delhi are always visible.
-   Hover details, an insight sentence, and a collapsed state table.

### 4. Sales Forecasting

Forecasts always come with a likely range (80%).

-   **Next day:** the saved cyclic-feature Linear Regression model, shown next to the 30-day average.
-   **Next 30 days and next 3 months:** the average of the last 365 days with a range from resampling past days.
-   **How well did it do?** Actual against forecast on days the model had not seen, a comparison with simple averages, how often the 80% range held, and a plain-language verdict.
-   Recent days and the forecast in a table, and a short description of how the forecast is made.

------------------------------------------------------------------------

## Design Decisions

**One definition of sales.** "Sales" means the recorded `Total_Amount` of **delivered** orders everywhere by default. An earlier version of the Sales Analysis page added up every order, including cancelled and returned ones, and showed ₹593.07 crore beside the Overview's ₹474.16 crore. Now the Sales Analysis page labels the scope and defaults to Delivered.

**Forecasts ignore the sidebar filters.** The saved model was trained on all-state daily totals. Feeding it one state's history gives meaningless numbers (in a test with a Delhi-only history, a model of this kind predicted roughly 20 times the real level).

**Ranges, not single numbers.** Daily sales vary by about ±12% around their average, so a single-day number alone would suggest more precision than exists.

**The model is tested against simple averages.** A forecasting model that does not beat a plain average adds complexity without value. The dashboard reports that comparison and states the result.

**Shared building blocks.** Colours, number formats, KPI cards, ranked bars and chart style live in one module, and data preparation and the previous-period comparison live in another, so all pages use the same definitions.

------------------------------------------------------------------------

## Technology Stack

  Area                       Tools
  -------------------------- --------------------------------
  Language                   Python
  Data manipulation          Pandas, NumPy
  Visualization              Plotly
  Dashboard                  Streamlit 1.65 or newer
  Machine learning           scikit-learn
  Model persistence          Joblib
  Geographic visualization   GeoJSON
  Development                Jupyter Notebook, VS Code, Git

------------------------------------------------------------------------

## Dataset

**Dataset:** [Indian E-Commerce Sales Analytics Dataset on Kaggle](https://www.kaggle.com/datasets/jatinkhandelwal112/indian-e-commerce-sales-analytics-dataset)

The project uses three CSV files:

  File                   Rows Purpose
  ----------------- --------- -----------------------------------
  `sales.csv`         250,000 Order-level sales and status data
  `customers.csv`      40,000 Customer attributes
  `products.csv`        2,000 Product attributes

The available order dates run from **1 June 2024 to 30 June 2026**.

### Data preparation notes

-   Order dates are converted to datetime values.
-   Sales amounts are converted to numeric values for analysis.
-   Delivered-order sales are used as the forecasting target.
-   Missing dates in the daily forecasting series are filled with zero so that calendar lag features can be constructed consistently.
-   The source data contains missing ratings and some negative recorded order amounts. These are dataset-quality considerations and should be interpreted rather than silently treated as confirmed business facts.
-   `Total_Amount` is a **recorded order amount** (order value minus coupon discount plus shipping), not confirmed profit or audited accounting revenue.

------------------------------------------------------------------------

## Selected Findings

All figures below are dataset-level observations, not independently audited business results.

### Orders and sales

-   **250,000** unique order IDs.
-   **39,914** unique customer IDs in the sales data; the customer table contains **40,000** customer IDs.
-   **200,139 delivered orders**, approximately **80.06%** of all orders.
-   Delivered orders have a combined recorded amount of approximately **₹474.16 crore**. Across all statuses it is approximately **₹593.07 crore**.
-   Cancellation and return records each represent approximately **5%** of orders. Returned or cancelled shares stay within roughly **4.7% to 5.2%** in every state, category and payment mode, so no group stands out.
-   Approximately **51.99%** of rating values are missing.

### What sells

-   Electronics represents approximately **72.6%** of the recorded amount for delivered orders, and that share stays between about **71.5% and 74.1%** in every month.
-   The average delivered order ranges from about **₹918** (Books) to about **₹64,269** (Electronics), so category largely decides the price tier.
-   Fashion has the highest delivered order count among the reported product categories.
-   The data holds 2,000 products across 33 brands.

### Order size and payment

-   The average delivered order is about **₹23,691**, but the **median is about ₹8,332**. The largest 10% of delivered orders bring in roughly **48%** of delivered sales.
-   UPI is the most common payment mode (about **51.4%** of orders), followed by cash on delivery (**32.8%**), debit card (**11.5%**) and credit card (**4.2%**).
-   Credit-card orders look larger on average, but that comes from product mix: credit-card buyers choose more Electronics, and within Electronics the average order is about ₹64K for every payment mode.
-   About **20%** of orders use a coupon, costing about **1%** of order value.

### Fulfilment

-   Delivery takes **2 to 7 days** (about 4.5 on average) and is the same in every state.

### Daily sales behave like noise

-   Delivered sales average about **₹62 lakh per day** and vary by roughly ±12%.
-   Sales on one day say almost nothing about the next: the correlation with the previous day is about 0, and about 0 a week apart.
-   Daily order counts vary almost exactly like random arrivals (variance divided by mean is about 1.0).
-   There is no visible trend, weekly pattern or yearly pattern. This may reflect how the dataset was produced.
-   Monthly totals are far more predictable than daily ones: "daily average times days in the month" missed by about **1.8%** on average over 22 completed months.

------------------------------------------------------------------------

## Forecasting Approach

### Target

The model predicts **daily delivered sales**, calculated by summing `Total_Amount` for orders whose status is `Delivered`.

### Model

-   **Algorithm:** `LinearRegression` from scikit-learn.
-   **Feature design:** cyclic calendar features, lagged sales, and rolling averages.
-   **Saved artifact:** `models/sales_forecasting_cyclic_model.pkl`, trained on all available history. The feature list is stored in the artifact alongside the estimator.

The ten model features are:

1.  `Day_Of_Week_Sin`
2.  `Day_Of_Week_Cos`
3.  `Day_Of_Year_Sin`
4.  `Day_Of_Year_Cos`
5.  `Sales_Lag_1`
6.  `Sales_Lag_7`
7.  `Sales_Lag_14`
8.  `Sales_Lag_30`
9.  `Rolling_Mean_7`
10. `Rolling_Mean_30`

The rolling means use earlier days only, so a day's own sales never leak into its features.

### Horizons

-   **Next day:** the saved model.
-   **Next 30 days and next 3 months:** the average of the last 365 days. The model was only ever validated one day ahead, so it is not extended further.
-   **Ranges (80%):** for the next day, from the model's past errors; for longer horizons, from resampling past days.

### Evaluation

The saved model has already seen every day in the data, so scoring it on the same days would flatter it. The Forecasting page therefore refits the same recipe on the first 80% of usable days (584 days) and scores it on the last 20% (**146 days, 5 February to 30 June 2026**). Each prediction uses actual earlier days as inputs, which is the same protocol as the development notebook.

  Method                              Typical daily miss (MAE)   Error (MAPE)
  ----------------------------------- -------------------------- --------------
  Long-run average                    ₹5.64 lakh                 9.0%
  30-day average                      ₹5.75 lakh                 9.2%
  Cyclic-feature Linear Regression    ₹5.75 lakh                 9.3%
  Previous day                        ₹7.12 lakh                 11.4%

**Result:** the model is about as accurate as a simple average, and clearly better than repeating yesterday's number. Because day-to-day sales behave like random noise, no more elaborate model is likely to do much better on this dataset.

The 80% range contained the actual sales on about **75%** of the unseen days (a well-calibrated range gives about 80%).

> **Note:** an earlier run of the development notebook recorded a test MAE of about ₹569,620. Re-running the same code on the current `sales.csv` gives about ₹575,069, which is the figure above. Re-run `notebooks/02_sales_forecasting.ipynb` from top to bottom to refresh its stored outputs and the saved model.

These results describe one-day-ahead prediction with actual earlier days as inputs. They do not establish the accuracy of recursive multi-day forecasts.

### Example from the end of the available dataset

The page shows a prediction of approximately **₹62.35 lakh for 1 July 2026**, with a likely range of roughly ₹53 to ₹72 lakh. For comparison, the latest actual day (30 June 2026) was approximately **₹64.02 lakh** and the 30-day average approximately **₹63.31 lakh**.

This example is tied to the dataset ending on 30 June 2026. It should not be described as a current-day forecast unless the dataset and model inputs are updated and the forecast is regenerated.

------------------------------------------------------------------------

## Project Structure

The core application files are organized as follows:

``` text
sales-data-business-insights/
├── app.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── data/
│   ├── sales.csv
│   ├── customers.csv
│   ├── products.csv
│   ├── india_states.geojson
│   └── india_states_simplified.geojson
├── models/
│   ├── forecast_features.pkl
│   ├── sales_forecasting_cyclic_model.pkl
│   └── sales_forecasting_model.pkl
├── utils/
│   ├── analytics.py
│   ├── data_loader.py
│   ├── filters.py
│   ├── styles.py
│   └── ui.py
├── views/
│   ├── overview.py
│   ├── sales_analysis.py
│   ├── india_sales_map.py
│   └── forecasting.py
└── notebooks/
    ├── 01_data_understanding.ipynb
    └── 02_sales_forecasting.ipynb
```

What the shared modules do:

-   `utils/data_loader.py`: loads and cleans the three CSV files once and caches them.
-   `utils/analytics.py`: shared data preparation, the "delivered" definition, and the previous-period comparison used by several pages.
-   `utils/filters.py`: the sidebar date-range and state filters.
-   `utils/ui.py`: the palette, number formats (₹ crore, lakh), KPI cards, ranked bars and chart style used by every page.
-   `utils/styles.py`: the global theme CSS.
-   `.streamlit/config.toml`: the light theme and the navy sidebar.

Additional notebooks and output files may exist in the working project.

------------------------------------------------------------------------

## Installation and Setup

### Prerequisites

-   Python 3.12 recommended for the environment used during development.
-   Streamlit **1.65 or newer** (the app uses `st.segmented_control`, `st.pills`, keyed containers and `width="stretch"`).
-   Git (optional, for version control).
-   The project files and dataset CSVs.
-   The saved model artifact under `models/`.

### 1. Clone or download the project

If the project is on GitHub:

``` bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd sales-data-business-insights
```

Alternatively, open the existing project folder in VS Code.

### 2. Create a virtual environment

**Windows, Git Bash:**

``` bash
python -m venv .venv
source .venv/Scripts/activate
```

**Windows, Command Prompt:**

``` bat
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

``` bash
python -m pip install -r requirements.txt
```

`requirements.txt` should contain at least:

``` text
streamlit>=1.65
pandas
numpy
plotly
scikit-learn
joblib
```

Pin the versions you have tested before sharing or deploying. The saved model is a scikit-learn pickle, so the scikit-learn version should match the one used to train it.

### 4. Check the project files

Confirm that the following files exist:

``` text
data/sales.csv
data/customers.csv
data/products.csv
data/india_states_simplified.geojson
models/sales_forecasting_cyclic_model.pkl
.streamlit/config.toml
```

Keep the filenames and relative folder structure consistent with the code.

------------------------------------------------------------------------

## Run the Dashboard

From the project root, with the virtual environment activated:

``` bash
streamlit run app.py
```

Streamlit will print a local URL, usually:

``` text
http://localhost:8501
```

Open that URL in your browser. Stop the local server with `Ctrl+C` in the terminal. After changing `.streamlit/config.toml`, restart the app, because the theme is only read at startup.

------------------------------------------------------------------------

## How to Use

1.  Start the app using the command above.
2.  Move between the Overview, Sales Analysis, India Sales Map and Forecasting pages from the sidebar.
3.  Use the quick-range control or the calendar for dates, and "Choose states" to narrow the states. These filters apply to the first three pages.
4.  On the Overview, switch the trend between Daily, Weekly and Monthly.
5.  On Sales Analysis, switch between **Delivered** and **All orders** to see how the totals change.
6.  On the India Sales Map, switch the colour between sales, orders and average order, and read the ranking beside the map.
7.  On Forecasting, choose a horizon (next day, next 30 days, next 3 months) and read the range as well as the central number. Open "How well did it do?" for the comparison with simple averages.

------------------------------------------------------------------------

## Validation and Limitations

Headline figures were cross-checked between pages: for example, delivered sales of ₹474.16 crore and 200,139 delivered orders appear on the Overview, Sales Analysis and India Sales Map pages.

Known considerations:

-   The dashboard is based on a finite historical dataset; the example data ends on 30 June 2026.
-   Daily sales in this dataset behave like random noise around a stable average. This limits any forecasting model and may reflect how the dataset was produced rather than real business behaviour.
-   The model was validated one day ahead only. Longer horizons use the 365-day average, and the 30-day and 3-month ranges come from resampling past days.
-   The 80% ranges describe how past days behaved; they are not guarantees. On unseen test days the daily range held about 75% of the time.
-   Missing dates filled with zero are an assumption about days without observed delivered orders; confirm this interpretation against the business data source before using the model operationally.
-   Recorded order amounts are not the same as profit.
-   Dataset inconsistencies and missing values can affect conclusions.
-   The state filter does not apply on the Forecasting page, because the saved model works on all-state daily totals.
-   The saved model uses Python serialization. Load pickle/joblib artifacts only from sources you trust, and keep compatible package versions when moving the project to another environment.

------------------------------------------------------------------------

## Future Improvements

-   Pin tested dependency versions in `requirements.txt`.
-   Add dashboard screenshots and a short demo video.
-   Replace the sidebar page selector with Streamlit's native multipage navigation.
-   Add a customer-segmentation page (for example, RFM segments).
-   Add CSV download for the detailed tables.
-   Add automated tests for data preparation, feature generation and forecast outputs.
-   Improve handling of missing dates, negative amounts and inconsistent source records with documented business rules.
-   Re-run the development notebook so its stored metrics match the current data, then re-save the model.
-   Add a repeatable data-refresh and model-retraining workflow.

------------------------------------------------------------------------

## Author

**Ganesh Chandra Rana**

This project demonstrates practical work in data analysis, interactive dashboards, geographic visualization, and introductory machine-learning forecasting.

-   **GitHub:** https://github.com/RanaForge
-   **Portfolio:** https://ranaforge.github.io/ganesh-portfolio/
-   **LinkedIn:** https://www.linkedin.com/in/gcr501

------------------------------------------------------------------------

## Acknowledgements

-   Dataset: [Indian E-Commerce Sales Analytics Dataset on Kaggle](https://www.kaggle.com/datasets/jatinkhandelwal112/indian-e-commerce-sales-analytics-dataset)
-   Open-source libraries: Streamlit, Pandas, NumPy, Plotly, scikit-learn, and Joblib.
