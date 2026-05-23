import json
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class ChartEngine:
    THEME = "plotly_dark"

    @staticmethod
    def _to_json(fig: go.Figure) -> dict:
        return json.loads(fig.to_json())

    @staticmethod
    def auto_chart(df: pd.DataFrame, x: str, y: str | None = None, title: str = "") -> dict:
        """Pick chart type automatically based on column dtypes."""
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        datetime_cols = df.select_dtypes(include="datetime").columns.tolist()

        # Time series: date x + numeric y
        if x in datetime_cols and y and y in numeric_cols:
            return ChartEngine.line_chart(df, x, y, title)

        x_dtype = df[x].dtype
        y_col = y

        if y_col and pd.api.types.is_numeric_dtype(df[y_col]):
            if pd.api.types.is_object_dtype(x_dtype) or pd.api.types.is_categorical_dtype(x_dtype):
                return ChartEngine.bar_chart(df, x, y_col, title)
            else:
                return ChartEngine.scatter_chart(df, x, y_col, title)
        elif not y_col and pd.api.types.is_numeric_dtype(df[x]):
            return ChartEngine.histogram(df, x, title)
        else:
            return ChartEngine.bar_chart(df, x, y_col or x, title)

    @staticmethod
    def bar_chart(
        df: pd.DataFrame,
        x: str,
        y: str,
        title: str = "",
        color: str | None = None,
        orientation: str = "v",
    ) -> dict:
        fig = px.bar(
            df, x=x, y=y, title=title or f"{y} by {x}",
            color=color, orientation=orientation,
            template=ChartEngine.THEME,
        )
        fig.update_layout(xaxis_tickangle=-30)
        return ChartEngine._to_json(fig)

    @staticmethod
    def line_chart(
        df: pd.DataFrame,
        x: str,
        y: str | list[str],
        title: str = "",
        color: str | None = None,
    ) -> dict:
        fig = px.line(
            df, x=x, y=y, title=title or f"{y} over {x}",
            color=color, template=ChartEngine.THEME, markers=True,
        )
        return ChartEngine._to_json(fig)

    @staticmethod
    def scatter_chart(
        df: pd.DataFrame,
        x: str,
        y: str,
        title: str = "",
        color: str | None = None,
        size: str | None = None,
        trendline: bool = True,
    ) -> dict:
        fig = px.scatter(
            df, x=x, y=y, title=title or f"{x} vs {y}",
            color=color, size=size,
            trendline="ols" if trendline else None,
            template=ChartEngine.THEME,
        )
        return ChartEngine._to_json(fig)

    @staticmethod
    def histogram(
        df: pd.DataFrame,
        column: str,
        title: str = "",
        nbins: int = 30,
        color: str | None = None,
    ) -> dict:
        fig = px.histogram(
            df, x=column, title=title or f"Distribution of {column}",
            nbins=nbins, color=color,
            template=ChartEngine.THEME,
            marginal="box",
        )
        return ChartEngine._to_json(fig)

    @staticmethod
    def box_plot(
        df: pd.DataFrame,
        y: str,
        x: str | None = None,
        title: str = "",
    ) -> dict:
        fig = px.box(
            df, x=x, y=y, title=title or f"Box plot of {y}",
            template=ChartEngine.THEME, points="outliers",
        )
        return ChartEngine._to_json(fig)

    @staticmethod
    def pie_chart(df: pd.DataFrame, names: str, values: str, title: str = "") -> dict:
        top = df.nlargest(10, values) if len(df) > 10 else df
        fig = px.pie(
            top, names=names, values=values,
            title=title or f"{values} by {names}",
            template=ChartEngine.THEME,
        )
        return ChartEngine._to_json(fig)

    @staticmethod
    def heatmap(
        matrix: list[list[float]],
        labels: list[str],
        title: str = "Correlation Matrix",
    ) -> dict:
        import numpy as np
        z = np.array(matrix)
        fig = go.Figure(
            data=go.Heatmap(
                z=z, x=labels, y=labels,
                colorscale="RdBu", zmid=0,
                text=[[f"{v:.2f}" for v in row] for row in matrix],
                texttemplate="%{text}",
            )
        )
        fig.update_layout(title=title, template=ChartEngine.THEME)
        return ChartEngine._to_json(fig)

    @staticmethod
    def area_chart(df: pd.DataFrame, x: str, y: str | list[str], title: str = "") -> dict:
        fig = px.area(
            df, x=x, y=y, title=title or f"{y} over {x}",
            template=ChartEngine.THEME,
        )
        return ChartEngine._to_json(fig)

    @staticmethod
    def time_series_decomposition_chart(decomp_result: dict) -> dict:
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=["Trend", "Seasonal", "Residual"],
            shared_xaxes=True,
        )
        for i, key in enumerate(["trend", "seasonal", "residual"], start=1):
            if key in decomp_result:
                fig.add_trace(
                    go.Scatter(
                        x=decomp_result[key]["dates"],
                        y=decomp_result[key]["values"],
                        name=key.capitalize(),
                        mode="lines",
                    ),
                    row=i, col=1,
                )
        fig.update_layout(
            title="Time Series Decomposition",
            template=ChartEngine.THEME,
            height=600,
        )
        return ChartEngine._to_json(fig)

    @staticmethod
    def feature_importance_chart(importances: dict[str, float], title: str = "Feature Importances") -> dict:
        items = sorted(importances.items(), key=lambda x: x[1])
        fig = go.Figure(
            go.Bar(
                x=[v for _, v in items],
                y=[k for k, _ in items],
                orientation="h",
            )
        )
        fig.update_layout(title=title, template=ChartEngine.THEME, xaxis_title="Importance")
        return ChartEngine._to_json(fig)
