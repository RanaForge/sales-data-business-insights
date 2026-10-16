# SalesVision Dashboard

🚀 **Live Dashboard:** [Open SalesVision Dashboard](https://salesvision-dashboard-ranaforge.streamlit.app)

Explore interactive e-commerce sales analytics, business insights, India sales maps, and sales forecasting.

## Project Overview

### Indian E-Commerce Sales Analysis & Next-Day Sales Forecasting

SalesVision is an interactive data analytics dashboard built to explore
an Indian e-commerce sales dataset, identify business patterns,
visualize sales across Indian states, and demonstrate a one-day-ahead
sales forecasting model.

The project combines data analysis, interactive visualization, and a
machine-learning workflow in a single Streamlit application.

> **Forecasting note:** The current dataset covers **1 June 2024 through
> 30 June 2026**. The displayed next-day forecast of **1 July 2026** is
> a historical, dataset-end prediction---not a forecast for today's
> sales.

------------------------------------------------------------------------

## Table of Contents

-   [Project Overview](#project-overview)
-   [Business Objectives](#business-objectives)
-   [Dashboard Features](#dashboard-features)
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

## Project Overview

E-commerce businesses need to understand order performance, customer
purchasing patterns, product categories, payment preferences, and
geographic sales distribution. They can also use historical sales data
to develop forecasts that support planning.

SalesVision provides an interactive interface for exploring these
questions. It includes sales analysis, an India state-level sales map,
and a forecasting page powered by a saved scikit-learn model.

## Business Objectives

-   Analyze order volume, recorded order amounts, and order-status
    distribution.
-   Explore customer, product-category, payment-mode, and state-level
    patterns.
-   Visualize geographic differences in sales across Indian states.
-   Demonstrate a next-calendar-day prediction using historical
    delivered sales.
-   Present analytical findings in a dashboard that can be explored by
    changing filters.

## Dashboard Features

### 1. Overview

A high-level view of key sales and order metrics. Use this page to get a
quick picture of the dataset and order performance.

### 2. Sales Analysis

Interactive analysis of sales and order patterns, including breakdowns
by relevant business dimensions.

### 3. India Sales Map

A geographic view of sales by state using GeoJSON state boundaries. A
simplified GeoJSON file is included to reduce rendering overhead and
improve map responsiveness.

### 4. Sales Forecasting

A one-day-ahead prediction of delivered sales using a saved
cyclic-feature Linear Regression model. The page displays forecast KPIs,
historical daily delivered sales, a 30-day average reference line, a
forecast interpretation, recent daily values, and model information.

### Shared Filters

The application provides shared date and state filters. Forecast results
depend on the history passed to the forecasting page, so the selected
range must include sufficient consecutive dates for the lag features.

------------------------------------------------------------------------

## Technology Stack

  Area                       Tools
  -------------------------- --------------------------------
  Language                   Python
  Data manipulation          Pandas, NumPy
  Visualization              Plotly
  Dashboard                  Streamlit
  Machine learning           scikit-learn
  Model persistence          Joblib
  Geographic visualization   GeoJSON
  Development                Jupyter Notebook, VS Code, Git

------------------------------------------------------------------------

## Dataset

**Dataset:** [Indian E-Commerce Sales Analytics Dataset on
Kaggle](https://www.kaggle.com/datasets/jatinkhandelwal112/indian-e-commerce-sales-analytics-dataset)

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
-   Missing dates in the daily forecasting series are filled with zero
    so that calendar lag features can be constructed consistently.
-   The source data contains missing ratings and some negative recorded
    order amounts. These are dataset-quality considerations and should
    be interpreted rather than silently treated as confirmed business
    facts.
-   `Total_Amount` is treated as a **recorded order amount**, not
    confirmed profit or audited accounting revenue.

------------------------------------------------------------------------

## Selected Findings

The following findings were recorded during exploratory analysis of this
dataset:

-   **250,000** unique order IDs.
-   **39,914** unique customer IDs represented in the sales data; the
    customer table contains **40,000** customer IDs.
-   **200,139 delivered orders**, approximately **80.06%** of all
    orders.
-   The delivered orders have a combined recorded amount of
    approximately **₹474.16 crore**.
-   Across all statuses, the recorded amount is approximately **₹593.07
    crore**.
-   Cancellation and return records each represent approximately **5%**
    of orders.
-   UPI is the most common payment mode, accounting for approximately
    **51.39%** of orders.
-   Electronics represents approximately **72.62%** of the recorded
    amount for delivered orders.
-   Fashion has the highest delivered order count among the reported
    product categories.
-   Approximately **51.99%** of rating values are missing.

These are dataset-level observations, not independently audited business
results. Figures can vary depending on filters, cleaning decisions, and
whether analysis includes all statuses or delivered orders only.

------------------------------------------------------------------------

## Forecasting Approach

### Target

The model predicts **daily delivered sales**, calculated by summing
`Total_Amount` for orders whose status is `Delivered`.

### Model

-   **Algorithm:** `LinearRegression` from scikit-learn.
-   **Feature design:** cyclic calendar features, lagged sales, and
    rolling averages.
-   **Forecast horizon:** one calendar day ahead.
-   **Saved artifact:** `models/sales_forecasting_cyclic_model.pkl`.
-   **Feature list:** stored in the model artifact alongside the
    estimator.

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

The dashboard builds these features in the same order as the saved
artifact and uses the most recent available daily history to produce the
next-day estimate.

### Recorded evaluation

The development notebook recorded approximately:

-   **MAE:** ₹569,619.94 per day
-   **RMSE:** ₹696,516.39 per day

These metrics should be read in the context of the notebook's evaluation
design. The reported evaluation used rolling one-day-ahead predictions
with actual preceding-day observations; it is not an untouched future
holdout evaluation and does not establish recursive multi-day forecast
accuracy.

### Example from the end of the available dataset

The dashboard previously displayed a prediction of approximately
**₹62.35 lakh for 1 July 2026**, compared with approximately **₹64.02
lakh** for the latest actual day and a 30-day average of approximately
**₹63.31 lakh**.

This example is tied to the dataset ending on 30 June 2026. It should
not be described as a current-day forecast unless the dataset and model
inputs are updated and the forecast is regenerated.

------------------------------------------------------------------------

## Project Structure

The core application files are organized as follows:

``` text
sales-data-business-insights/
├── app.py
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
│   ├── data_loader.py
│   ├── styles.py
│   └── date_filter.py
├── views/
│   ├── overview.py
│   ├── sales_analysis.py
│   ├── india_sales_map.py
│   └── forecasting.py
└── notebooks/
    └── 02_sales_forecasting.ipynb
```

Additional notebooks and output files may exist in the working project.

------------------------------------------------------------------------

## Installation and Setup

### Prerequisites

-   Python 3.12 recommended for the environment used during development.
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

**Windows --- Git Bash:**

``` bash
python -m venv .venv
source .venv/Scripts/activate
```

**Windows --- Command Prompt:**

``` bat
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

If a `requirements.txt` file is available:

``` bash
python -m pip install -r requirements.txt
```

If one has not been created yet, install the core packages:

``` bash
python -m pip install streamlit pandas numpy plotly scikit-learn joblib
```

Depending on the other pages in your project, additional packages may be
required. Add all confirmed project dependencies to `requirements.txt`
before sharing or deploying the application.

### 4. Check the project files

Confirm that the following files exist:

``` text
data/sales.csv
data/customers.csv
data/products.csv
models/sales_forecasting_cyclic_model.pkl
data/india_states_simplified.geojson
```

The full GeoJSON file may also be required by the map implementation.
Keep the filenames and relative folder structure consistent with the
code.

------------------------------------------------------------------------

## Run the Dashboard

From the project root, with the virtual environment activated:

``` bash
streamlit run app.py
```

Streamlit will print a local URL in the terminal, usually:

``` text
http://localhost:8501
```

Open that URL in your browser. Stop the local server with `Ctrl+C` in
the terminal.

------------------------------------------------------------------------

## How to Use

1.  Start the app using the command above.
2.  Navigate between the Overview, Sales Analysis, India Sales Map, and
    Forecasting pages.
3.  Adjust the shared date and state filters to explore the available
    records.
4.  Compare order statuses, recorded sales amounts, payment modes,
    product categories, and state-level patterns.
5.  Open the Forecasting page to review the next-day estimate, recent
    daily history, 30-day average, and model details.
6.  Interpret the forecast as an estimate rather than a guaranteed
    outcome.

------------------------------------------------------------------------

## Validation and Limitations

The dashboard's core pages and filters have been manually validated in
the local development environment.

Known considerations:

-   The dashboard is based on a finite historical dataset; the example
    data ends on 30 June 2026.
-   The forecasting model needs sufficient consecutive daily history to
    calculate its lag and rolling features.
-   Missing dates filled with zero are an assumption about days without
    observed delivered orders; confirm this interpretation against the
    business data source before using the model operationally.
-   Recorded order amounts are not the same as profit.
-   Dataset inconsistencies and missing values can affect conclusions.
-   Forecast evaluation from the development notebook is not a guarantee
    of future performance.
-   The saved model uses Python serialization. Load pickle/joblib
    artifacts only from sources you trust, and keep compatible package
    versions when moving the project to another environment.

------------------------------------------------------------------------

## Future Improvements

-   Add a `requirements.txt` with pinned, tested dependencies.
-   Deploy the dashboard and document the live URL.
-   Add dashboard screenshots and a short demo video.
-   Evaluate the forecasting model using a strictly time-based holdout
    period and compare it with simple baselines.
-   Add prediction intervals or uncertainty communication where
    methodologically justified.
-   Add automated tests for data preparation, feature generation, and
    forecast outputs.
-   Improve handling of missing dates, negative amounts, and
    inconsistent source records with documented business rules.
-   Add a repeatable data-refresh and model-retraining workflow.

------------------------------------------------------------------------

## Author

**Ganesh Chandra Rana**

This project demonstrates practical work in data analysis, interactive
dashboards, geographic visualization, and introductory machine-learning
forecasting.

-   **GitHub:** https://github.com/RanaForge.
-   **Portfolio:** https://ranaforge.github.io/ganesh-portfolio/.
-   **LinkedIn:** https://www.linkedin.com/in/gcr501.

------------------------------------------------------------------------

## Acknowledgements

-   Dataset: [Indian E-Commerce Sales Analytics Dataset ---
    Kaggle](https://www.kaggle.com/datasets/jatinkhandelwal112/indian-e-commerce-sales-analytics-dataset)
-   Open-source libraries: Streamlit, Pandas, NumPy, Plotly,
    scikit-learn, and Joblib.
