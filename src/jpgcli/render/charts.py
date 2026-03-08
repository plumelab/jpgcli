from __future__ import annotations

from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
import pandas as pd
import seaborn as sns

from jpgcli.schemas.chart_spec import Aggregation, ChartSpec, ChartType, ErrorBarStyle, LegendPosition, RenderTheme, SortOrder
from jpgcli.utils.errors import RenderError, SpecValidationError
from jpgcli.render.fonts import has_cjk_font, resolve_font_stack
from jpgcli.render.themes import THEMES


class ChartRenderer:
    def render(
        self,
        dataframe: pd.DataFrame,
        spec: ChartSpec,
        output_path: Path,
        *,
        theme: RenderTheme,
        width: float = 10,
        height: float = 6,
        dpi: int = 300,
        override_title: str | None = None,
    ) -> Path:
        self._validate_columns(dataframe, spec)
        prepared = self._prepare_data(dataframe, spec)
        theme_config = THEMES[theme]
        plot_frame = self._plot_frame(dataframe, prepared, spec)
        x_order = self._category_order(prepared, spec.x)
        font_stack = resolve_font_stack()

        sns.set_theme(style="whitegrid")
        plt.rcParams.update(
            {
                "figure.facecolor": theme_config.background,
                "axes.facecolor": theme_config.background,
                "grid.color": theme_config.grid_color,
                "font.family": "sans-serif",
                "font.sans-serif": font_stack,
                "axes.unicode_minus": False,
            }
        )
        if not has_cjk_font():
            warnings.warn("No CJK font detected; Chinese text may render incorrectly.", stacklevel=2)

        figure_width, figure_height = self._resolve_figure_size(plot_frame, spec, width, height, x_order=x_order)
        fig, ax = plt.subplots(figsize=(figure_width, figure_height), dpi=dpi)
        fig.patch.set_facecolor(theme_config.background)
        ax.set_facecolor(theme_config.background)
        primary_color = theme_config.palette[0]
        palette = self._resolve_palette(spec, theme_config.palette, plot_frame, spec.series)

        if spec.chart_type == ChartType.BAR:
            self._render_barplot(ax, plot_frame, spec, primary_color, x_order=x_order)
        elif spec.chart_type == ChartType.GROUPED_BAR:
            if not spec.series:
                raise RenderError("grouped_bar requires a series column.")
            self._render_grouped_barplot(ax, plot_frame, spec, palette, x_order=x_order)
        elif spec.chart_type == ChartType.LINE:
            lineplot_kwargs = {
                "data": plot_frame,
                "x": spec.x,
                "y": spec.y,
                "marker": "o",
                "linewidth": 2.2,
                "ax": ax,
            }
            if spec.series:
                lineplot_kwargs["hue"] = spec.series
                lineplot_kwargs["palette"] = palette
            else:
                lineplot_kwargs["color"] = primary_color
            if self._has_replicates(dataframe, spec):
                lineplot_kwargs["errorbar"] = self._resolve_errorbar(spec)
            sns.lineplot(**lineplot_kwargs)
            if self._resolve_show_points(plot_frame, spec):
                self._overlay_scatter_points(ax, plot_frame, spec, palette=palette, default_color=primary_color, size=55)
        elif spec.chart_type == ChartType.SCATTER:
            scatterplot_kwargs = {
                "data": plot_frame,
                "x": spec.x,
                "y": spec.y,
                "s": 90,
                "ax": ax,
            }
            if spec.series:
                scatterplot_kwargs["hue"] = spec.series
                scatterplot_kwargs["palette"] = palette
            else:
                scatterplot_kwargs["color"] = primary_color
            sns.scatterplot(**scatterplot_kwargs)
        elif spec.chart_type == ChartType.AREA:
            self._render_area_plot(ax, plot_frame, spec, palette=palette, default_color=primary_color, x_order=x_order)
        elif spec.chart_type == ChartType.BOXPLOT:
            self._render_boxplot(ax, dataframe, spec, palette=palette, x_order=x_order)
        else:
            raise RenderError(f"Unsupported chart type: {spec.chart_type}")

        title = override_title or spec.title or "Generated Chart"
        ax.set_title(title, fontsize=theme_config.title_size, loc="left", pad=18, weight="bold")
        if spec.subtitle:
            ax.text(0.0, 1.02, spec.subtitle, transform=ax.transAxes, fontsize=theme_config.subtitle_size, alpha=0.85)
        ax.set_xlabel(spec.x_label or self._format_axis_label(spec.x), fontsize=theme_config.label_size)
        ax.set_ylabel(spec.y_label or self._format_axis_label(spec.y or ""), fontsize=theme_config.label_size)
        ax.tick_params(axis="both", labelsize=theme_config.tick_size)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.grid(axis="y", linewidth=0.8)
        ax.grid(axis="x", visible=False)
        ax.margins(x=0.03)
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        self._format_x_ticks(ax, plot_frame, spec)
        if spec.series:
            legend = self._set_series_legend(ax, spec, theme_config.legend_size)
            if legend:
                legend.set_title(spec.legend_title or self._format_axis_label(spec.series))
        if spec.y_min is not None or spec.y_max is not None:
            ax.set_ylim(bottom=spec.y_min, top=spec.y_max)
        if spec.caption:
            fig.text(0.01, 0.01, spec.caption, ha="left", va="bottom", fontsize=9, alpha=0.8)

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def _validate_columns(self, dataframe: pd.DataFrame, spec: ChartSpec) -> None:
        for column_name in [spec.x, spec.y, spec.series]:
            if column_name and column_name not in dataframe.columns:
                raise SpecValidationError(f"Column not found in data: {column_name}")

    def _prepare_data(self, dataframe: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        frame = dataframe.copy()
        if spec.aggregation != Aggregation.NONE:
            if not spec.y:
                raise RenderError("Aggregation requires a y column.")
            group_columns = [spec.x] + ([spec.series] if spec.series else [])
            grouped = frame.groupby(group_columns, dropna=False)[spec.y]
            if spec.aggregation == Aggregation.SUM:
                frame = grouped.sum().reset_index()
            elif spec.aggregation == Aggregation.MEAN:
                frame = grouped.mean().reset_index()
            elif spec.aggregation == Aggregation.COUNT:
                frame = grouped.count().reset_index()
            elif spec.aggregation == Aggregation.MEDIAN:
                frame = grouped.median().reset_index()
        if frame.empty:
            raise RenderError("No data available after preprocessing.")
        if spec.sort != SortOrder.NONE:
            sort_column = spec.y if spec.y else spec.x
            ascending = spec.sort == SortOrder.ASC
            frame = frame.sort_values(by=sort_column, ascending=ascending)
        return frame

    def _plot_frame(self, raw: pd.DataFrame, prepared: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        if spec.chart_type in {ChartType.BAR, ChartType.GROUPED_BAR, ChartType.LINE} and self._can_use_raw_distribution(spec):
            return raw.copy()
        if spec.chart_type == ChartType.BOXPLOT:
            return raw.copy()
        return prepared

    def _render_barplot(
        self,
        ax,
        dataframe: pd.DataFrame,
        spec: ChartSpec,
        color: str,
        *,
        x_order: list[str] | None,
    ) -> None:
        kwargs = {"data": dataframe, "x": spec.x, "y": spec.y, "color": color, "ax": ax}
        if self._can_use_raw_distribution(spec):
            kwargs["estimator"] = "mean"
            kwargs["errorbar"] = self._resolve_errorbar(spec)
            kwargs["order"] = x_order
        sns.barplot(**kwargs)
        if spec.annotate_values:
            self._annotate_bar_values(ax)
        if self._resolve_show_points(dataframe, spec):
            sns.stripplot(
                data=dataframe,
                x=spec.x,
                y=spec.y,
                order=x_order,
                color="#1f1f1f",
                alpha=0.65,
                size=4,
                jitter=0.12,
                ax=ax,
            )

    def _render_grouped_barplot(
        self,
        ax,
        dataframe: pd.DataFrame,
        spec: ChartSpec,
        palette: list[str],
        *,
        x_order: list[str] | None,
    ) -> None:
        series_order = self._category_order(dataframe, spec.series) or []
        active_palette = palette[: max(len(series_order), 1)]
        kwargs = {
            "data": dataframe,
            "x": spec.x,
            "y": spec.y,
            "hue": spec.series,
            "palette": active_palette,
            "ax": ax,
            "order": x_order,
            "hue_order": series_order or None,
        }
        if self._can_use_raw_distribution(spec):
            kwargs["estimator"] = "mean"
            kwargs["errorbar"] = self._resolve_errorbar(spec)
        sns.barplot(**kwargs)
        if spec.annotate_values:
            self._annotate_bar_values(ax)
        if self._resolve_show_points(dataframe, spec):
            sns.stripplot(
                data=dataframe,
                x=spec.x,
                y=spec.y,
                hue=spec.series,
                dodge=True,
                palette=active_palette,
                order=x_order,
                hue_order=series_order or None,
                alpha=0.6,
                size=3.8,
                linewidth=0.2,
                edgecolor="#23313f",
                ax=ax,
            )

    def _render_area_plot(
        self,
        ax,
        dataframe: pd.DataFrame,
        spec: ChartSpec,
        *,
        palette: list[str],
        default_color: str,
        x_order: list[str] | None,
    ) -> None:
        area_frame = self._aggregate_for_area(dataframe, spec)
        if spec.series:
            series_order = self._category_order(area_frame, spec.series) or sorted(area_frame[spec.series].dropna().unique().tolist())
            x_positions, tick_labels = self._resolve_x_positions(area_frame, spec.x, x_order)
            for index, series_value in enumerate(series_order):
                subset = area_frame[area_frame[spec.series] == series_value].copy()
                subset = self._sort_for_x(subset, spec.x, x_order)
                series_x = self._map_x_values(subset[spec.x], x_positions)
                color = palette[index % len(palette)]
                ax.plot(series_x, subset[spec.y], color=color, linewidth=2.4, marker="o", label=series_value)
                ax.fill_between(series_x, subset[spec.y], color=color, alpha=0.18)
            self._apply_categorical_ticks(ax, tick_labels)
        else:
            subset = self._sort_for_x(area_frame.copy(), spec.x, x_order)
            x_values, tick_labels = self._resolve_single_series_x(subset, spec.x, x_order)
            ax.plot(x_values, subset[spec.y], color=default_color, linewidth=2.4, marker="o")
            ax.fill_between(x_values, subset[spec.y], color=default_color, alpha=0.18)
            if tick_labels is not None:
                self._apply_categorical_ticks(ax, tick_labels)

    def _render_boxplot(
        self,
        ax,
        dataframe: pd.DataFrame,
        spec: ChartSpec,
        *,
        palette: list[str],
        x_order: list[str] | None,
    ) -> None:
        kwargs = {
            "data": dataframe,
            "x": spec.x,
            "y": spec.y,
            "ax": ax,
            "order": x_order,
            "showfliers": not self._resolve_show_points(dataframe, spec),
            "linewidth": 1.2,
        }
        if spec.series:
            series_order = self._category_order(dataframe, spec.series) or None
            kwargs["hue"] = spec.series
            kwargs["hue_order"] = series_order
            kwargs["palette"] = palette[: max(len(series_order or []), 1)]
        else:
            kwargs["color"] = palette[0]
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="vert: bool will be deprecated in a future version.*",
                category=PendingDeprecationWarning,
            )
            sns.boxplot(**kwargs)
        if self._resolve_show_points(dataframe, spec):
            point_kwargs = {
                "data": dataframe,
                "x": spec.x,
                "y": spec.y,
                "order": x_order,
                "alpha": 0.55,
                "size": 3.4,
                "linewidth": 0.25,
                "edgecolor": "#23313f",
                "ax": ax,
            }
            if spec.series:
                point_kwargs["hue"] = spec.series
                point_kwargs["hue_order"] = self._category_order(dataframe, spec.series) or None
                point_kwargs["palette"] = palette
                point_kwargs["dodge"] = True
            else:
                point_kwargs["color"] = "#1f1f1f"
            sns.stripplot(**point_kwargs)

    def _can_use_raw_distribution(self, spec: ChartSpec) -> bool:
        return spec.aggregation in {Aggregation.NONE, Aggregation.MEAN}

    def _resolve_show_points(self, dataframe: pd.DataFrame, spec: ChartSpec) -> bool:
        if spec.show_points is not None:
            return spec.show_points
        if spec.chart_type in {ChartType.SCATTER, ChartType.BOXPLOT}:
            return True
        return self._can_use_raw_distribution(spec) and self._has_replicates(dataframe, spec)

    def _has_replicates(self, dataframe: pd.DataFrame, spec: ChartSpec) -> bool:
        group_columns = [spec.x] + ([spec.series] if spec.series else [])
        if not group_columns or not spec.y:
            return False
        group_sizes = dataframe.groupby(group_columns, dropna=False).size()
        return bool((group_sizes > 1).any())

    def _category_order(self, dataframe: pd.DataFrame, column_name: str) -> list[str] | None:
        if column_name not in dataframe.columns:
            return None
        series = dataframe[column_name]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            return None
        return [value for value in series.drop_duplicates().tolist()]

    def _set_series_legend(self, ax, spec: ChartSpec, legend_size: int):
        handles, labels = ax.get_legend_handles_labels()
        if not handles:
            return None
        unique = {}
        for handle, label in zip(handles, labels):
            if label.startswith("_"):
                continue
            unique.setdefault(label, handle)
        if not unique:
            return None
        return ax.legend(
            unique.values(),
            unique.keys(),
            frameon=False,
            fontsize=legend_size,
            loc=self._legend_location(spec.legend_position),
        )

    def _format_x_ticks(self, ax, dataframe: pd.DataFrame, spec: ChartSpec) -> None:
        if spec.x not in dataframe.columns:
            return
        series = dataframe[spec.x]
        if spec.rotate_xticks is not None:
            ax.tick_params(axis="x", rotation=spec.rotate_xticks)
            return
        if pd.api.types.is_datetime64_any_dtype(series):
            ax.tick_params(axis="x", rotation=30)
            return
        if series.astype(str).map(len).max() > 12:
            ax.tick_params(axis="x", rotation=20)

    def _format_axis_label(self, raw_label: str) -> str:
        if not raw_label:
            return raw_label
        label = raw_label.strip()
        replacements = {
            "sod_activity_u_g_fw": r"SOD activity (U·g$^{-1}$ FW)",
            "od_value": "OD value",
            "plant_variety": "Plant variety",
            "days_after_treatment": "Days after treatment",
            "fresh_weight_g": "Fresh weight (g)",
            "extract_volume_ml": "Extract volume (mL)",
            "wavelength_nm": "Wavelength (nm)",
        }
        if label in replacements:
            return replacements[label]
        parts = label.replace("_", " ").split()
        formatted_parts = []
        for part in parts:
            if part.lower() in {"od", "sod", "pod", "cat", "fw"}:
                formatted_parts.append(part.upper())
            elif part.lower() in {"ml", "nm"}:
                formatted_parts.append(part.lower())
            else:
                formatted_parts.append(part.capitalize())
        return " ".join(formatted_parts)

    def _resolve_errorbar(self, spec: ChartSpec):
        if spec.error_bar == ErrorBarStyle.NONE:
            return None
        if spec.error_bar == ErrorBarStyle.SE:
            return "se"
        return "sd"

    def _resolve_palette(self, spec: ChartSpec, default_palette: list[str], dataframe: pd.DataFrame, series: str | None) -> list[str]:
        n_colors = max(len(self._category_order(dataframe, series) or []), 1)
        if spec.palette:
            try:
                return sns.color_palette(spec.palette, n_colors=n_colors)
            except ValueError:
                return default_palette[:n_colors]
        return default_palette[:n_colors] or default_palette

    def _legend_location(self, position: LegendPosition) -> str:
        mapping = {
            LegendPosition.BEST: "best",
            LegendPosition.UPPER_LEFT: "upper left",
            LegendPosition.UPPER_RIGHT: "upper right",
            LegendPosition.LOWER_LEFT: "lower left",
            LegendPosition.LOWER_RIGHT: "lower right",
        }
        return mapping[position]

    def _resolve_figure_size(
        self,
        dataframe: pd.DataFrame,
        spec: ChartSpec,
        width: float,
        height: float,
        *,
        x_order: list[str] | None,
    ) -> tuple[float, float]:
        if (width, height) != (10, 6):
            return width, height
        category_count = len(x_order or []) or max(dataframe[spec.x].nunique(), 1)
        series_count = len(self._category_order(dataframe, spec.series) or []) or 1
        if spec.chart_type in {ChartType.GROUPED_BAR, ChartType.BOXPLOT}:
            return min(max(8.8, 2.2 + 1.5 * category_count + 0.55 * series_count), 14.5), 6.2
        if spec.chart_type in {ChartType.LINE, ChartType.AREA}:
            return min(max(9.0, 3.2 + 1.15 * category_count), 14.0), 6.0
        return min(max(8.5, 3.0 + 1.2 * category_count), 13.5), 6.0

    def _annotate_bar_values(self, ax) -> None:
        for container in ax.containers:
            try:
                ax.bar_label(container, fmt="%.1f", padding=3, fontsize=9)
            except ValueError:
                continue

    def _overlay_scatter_points(
        self,
        ax,
        dataframe: pd.DataFrame,
        spec: ChartSpec,
        *,
        palette: list[str],
        default_color: str,
        size: int,
    ) -> None:
        kwargs = {"data": dataframe, "x": spec.x, "y": spec.y, "s": size, "ax": ax, "alpha": 0.65}
        if spec.series:
            kwargs["hue"] = spec.series
            kwargs["palette"] = palette
        else:
            kwargs["color"] = default_color
        sns.scatterplot(**kwargs)

    def _aggregate_for_area(self, dataframe: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        group_columns = [spec.x] + ([spec.series] if spec.series else [])
        grouped = dataframe.groupby(group_columns, dropna=False)[spec.y]
        if spec.aggregation == Aggregation.SUM:
            return grouped.sum().reset_index()
        if spec.aggregation == Aggregation.COUNT:
            return grouped.count().reset_index()
        if spec.aggregation == Aggregation.MEDIAN:
            return grouped.median().reset_index()
        return grouped.mean().reset_index()

    def _sort_for_x(self, dataframe: pd.DataFrame, column_name: str, x_order: list[str] | None) -> pd.DataFrame:
        if x_order:
            order_map = {value: index for index, value in enumerate(x_order)}
            return dataframe.assign(_sort_key=dataframe[column_name].map(order_map)).sort_values("_sort_key").drop(columns="_sort_key")
        return dataframe.sort_values(column_name)

    def _resolve_single_series_x(self, dataframe: pd.DataFrame, column_name: str, x_order: list[str] | None):
        series = dataframe[column_name]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            return series, None
        tick_labels = x_order or [str(value) for value in series.tolist()]
        mapping = {label: index for index, label in enumerate(tick_labels)}
        return series.astype(str).map(mapping), tick_labels

    def _resolve_x_positions(self, dataframe: pd.DataFrame, column_name: str, x_order: list[str] | None) -> tuple[dict[str, int], list[str] | None]:
        series = dataframe[column_name]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            unique = [str(value) for value in series.drop_duplicates().tolist()]
            return {value: index for index, value in enumerate(unique)}, None
        tick_labels = x_order or [str(value) for value in series.drop_duplicates().tolist()]
        return {label: index for index, label in enumerate(tick_labels)}, tick_labels

    def _map_x_values(self, series: pd.Series, positions: dict[str, int]):
        return series.astype(str).map(positions)

    def _apply_categorical_ticks(self, ax, tick_labels: list[str] | None) -> None:
        if not tick_labels:
            return
        ax.set_xticks(np.arange(len(tick_labels)))
        ax.set_xticklabels(tick_labels)
