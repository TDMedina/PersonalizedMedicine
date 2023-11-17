
from datetime import datetime

import pandas as pd
from pandas import IndexSlice as idx
from pandas.api.extensions import register_dataframe_accessor
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


@register_dataframe_accessor("survival")
class SurvivalData:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    @staticmethod
    def read_csv(survival_data):
        survival_data = pd.read_csv(survival_data, sep=",")
        survival_data = survival_data.loc[survival_data.Dates != "2009-2013"]
        survival_data = (survival_data
                         .sort_values(by="Time (years)")
                         .sort_values(by="Dates", ascending=False, kind="stable"))
        survival_data["Net survival"] = survival_data["Net survival"] / 100
        return survival_data

    def plot(self):
        survival_plot = px.line(self._obj, x="Time (years)", y="Net survival",
                                color="Dates", markers=True,
                                title=("Survival: All invasive cancers "
                                       "(except NMSC) in Ireland"),
                                width=750, height=500,
                                template="plotly_white")
        survival_plot.update_layout(legend_title="Date range")
        survival_plot.update_yaxes(tickformat=".0%", range=[0, 1])
        return survival_plot


# def read_survival(survival_data):
#     survival_data = pd.read_csv(survival_data, sep=",")
#     survival_data = survival_data.loc[survival_data.Dates != "2009-2013"]
#     survival_data = (survival_data
#                      .sort_values(by="Time (years)")
#                      .sort_values(by="Dates", ascending=False, kind="stable"))
#     survival_data["Net survival"] = survival_data["Net survival"] / 100
#     return survival_data
#
#
# def plot_survival(survival_data):
#     survival_plot = px.line(survival_data, x="Time (years)", y="Net survival",
#                             color="Dates", markers=True,
#                             title=("Survival: All invasive cancers "
#                                    "(except NMSC) in Ireland"),
#                             width=750, height=500,
#                             template="plotly_white")
#     survival_plot.update_layout(legend_title="Date range")
#     survival_plot.update_yaxes(tickformat=".0%", range=[0, 1])
#     return survival_plot


@register_dataframe_accessor("age_incidence")
class AgeIncidenceData:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    @staticmethod
    def read_csv(incidence_data):
        data = pd.read_csv(incidence_data, sep=",")
        data["Year"] =
        data = (data
                .sort_values(by="Year")
                .sort_values(by="Age band", ascending=False, kind="stable"))
        data.set_index(["Age band"], inplace=True)
        return data

    def plot(self, raw_count=False, combined=False):
        if combined:
            incidence_plot = self._plot_combined()
            return incidence_plot
        if raw_count:
            y = "Case numbers"
            y_title = "Cases per year"
        else:
            y = "Crude rate"
            y_title = "Cases per 100,000 per year (crude rate)"
        incidence_plot = px.line(self._obj, x="Year", y=y,
                                 color=self._obj.index.values,
                                 markers=True, width=750, height=500,
                                 title=("Incidence by age: All invasive cancers "
                                        "(except NMSC) in Ireland"),
                                 template="plotly_white")
        incidence_plot = incidence_plot.update_layout(yaxis_title=y_title,
                                                      legend_title="Age band")
        return incidence_plot

    def _plot_combined(self):
        raw = self.plot(raw_count=True)
        rel = self.plot(raw_count=False)

        age_plot = make_subplots(rows=1, cols=2,
                                 subplot_titles=["a) Cases per age band",
                                                 "b) Cases per 100K in age band"],
                                 x_title="Year",
                                 y_title="Cases")
        for i, plot in enumerate([raw, rel], start=1):
            for trace in plot.data:
                age_plot.add_trace(trace, row=1, col=i)

        age_plot.update_traces(showlegend=False, col=2)
        age_plot.update_layout(title=raw.layout.title.text,
                               legend=dict(
                                   title="Age band",
                                   # xanchor="center",
                                   # orientation="h",
                                   # x=0.5
                                   ),
                               template="plotly_white")
        age_plot.layout.annotations[0].update(xanchor="left", xshift=-190)
        age_plot.layout.annotations[1].update(xanchor="left", xshift=-190)
        # age_plot.update_annotations(xanchor="left", xshift=-190)

        return age_plot

# def read_age_incidence(incidence_data):
#     incidence_data = pd.read_csv(incidence_data, sep=",")
#     incidence_data = (incidence_data
#                       .sort_values(by="Year")
#                       .sort_values(by="Age band", ascending=False, kind="stable"))
#     incidence_data.set_index(["Age band"], inplace=True)
#     return incidence_data
#
#
# def plot_age_incidence(age_incidence_data, raw_count=False, combined=False):
#     if combined:
#         incidence_plot = _plot_combined_age_incidence(age_incidence_data)
#         return incidence_plot
#     if raw_count:
#         y = "Case numbers"
#         y_title = "Cases per year"
#     else:
#         y = "Crude rate"
#         y_title = "Cases per 100,000 per year (crude rate)"
#     incidence_plot = px.line(age_incidence_data, x="Year", y=y,
#                              color=age_incidence_data.index.values,
#                              markers=True, width=750, height=500,
#                              title=("Incidence by age: All invasive cancers "
#                                     "(except NMSC) in Ireland"),
#                              template="plotly_white")
#     incidence_plot = incidence_plot.update_layout(yaxis_title=y_title,
#                                                   legend_title="Age band")
#     return incidence_plot
#
#
# def _plot_combined_age_incidence(age_incidence_data):
#     raw = plot_age_incidence(age_incidence_data, raw_count=True)
#     rel = plot_age_incidence(age_incidence_data, raw_count=False)
#
#     age_plot = make_subplots(rows=1, cols=2,
#                              subplot_titles=["a) Cases per age band",
#                                              "b) Cases per 100K in age band"],
#                              x_title="Year",
#                              y_title="Cases")
#     for i, plot in enumerate([raw, rel], start=1):
#         for trace in plot.data:
#             age_plot.add_trace(trace, row=1, col=i)
#
#     age_plot.update_traces(showlegend=False, col=2)
#     age_plot.update_layout(title=raw.layout.title.text,
#                            legend=dict(
#                                title="Age band",
#                                # xanchor="center",
#                                # orientation="h",
#                                # x=0.5
#                                ),
#                            template="plotly_white")
#     age_plot.layout.annotations[0].update(x=0.07)
#     age_plot.layout.annotations[1].update(x=0.68)
#
#     # age_plot.update_xaxes(title_text="xaxis 1 title", row=1, col=1)
#
#     return age_plot


@register_dataframe_accessor("sex_incidence")
class SexIncidenceData:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    @classmethod
    def read_data(cls, sex_incidence_csv, population_csv):
        incidence = cls._read_sex_incidence_csv(sex_incidence_csv)
        population = cls._read_population_csv(population_csv)
        data = cls._merge_incidence_and_population_tables(incidence, population)
        return data

    @staticmethod
    def _read_sex_incidence_csv(sex_incidence_csv):
        incidence = pd.read_csv(sex_incidence_csv)
        incidence.set_index(["Year", "Sex"], inplace=True)
        incidence.rename(index={"Males": "Male", "Females": "Female"},
                         level="Sex", inplace=True)
        return incidence

    @staticmethod
    def _read_population_csv(population_csv, drop_subgroups=True):
        pop_data = pd.read_csv(population_csv, sep=",", usecols=[1, 2, 3, 5])
        cols = list(pop_data.columns)
        cols[-1] = "Population"
        pop_data.columns = cols
        pop_data["Population"] = pop_data["Population"] * 1000
        if drop_subgroups:
            pop_data = pop_data.loc[pop_data["Age Group"] == "All ages"]
            pop_data.drop("Age Group", axis=1, inplace=True)
            pop_data.set_index(["Year", "Sex"], inplace=True)
        else:
            pop_data.set_index(["Year", "Sex", "Age Group"], inplace=True)
        pop_data.sort_index(inplace=True)
        pop_data.rename(index={"Both sexes": "Both"}, level="Sex", inplace=True)
        return pop_data

    @staticmethod
    def _merge_incidence_and_population_tables(incidence, population):
        data = pd.merge(incidence, population, left_index=True, right_index=True)
        data["Relative numbers"] = data["Case numbers"] / data["Population"] * 100000
        return data

    def plot(self, raw_count=True, combined=False):
        if combined:
            incidence_plot = self._plot_combined()
            return incidence_plot
        if raw_count:
            y = "Case numbers"
            y_title = "Cases per year"
        else:
            y = "Relative numbers"
            y_title = "Cases per 100,000 total population per year"
        data = self._obj.reset_index()
        incidence_plot = px.line(data, x="Year", y=y, color="Sex",
                                 markers=True, width=750, height=500,
                                 title=("Total incidence: All invasive cancers "
                                        "(except NMSC) in Ireland"),
                                 template="plotly_white")
        incidence_plot.update_layout(yaxis_title=y_title)
        return incidence_plot

    def _plot_combined(self):
        raw = self.plot(raw_count=True)
        rel = self.plot(raw_count=False)

        sex_plot = make_subplots(rows=1, cols=2,
                                 subplot_titles=["a) Cases per sex",
                                                 "b) Cases per 100K of sex"],
                                 x_title="Year",
                                 y_title="Cases")
        for i, plot in enumerate([raw, rel], start=1):
            for trace in plot.data:
                sex_plot.add_trace(trace, row=1, col=i)

        sex_plot.update_traces(showlegend=False, col=2)
        sex_plot.update_layout(title=raw.layout.title.text,
                               legend=dict(
                                   title="Sex",
                                   # xanchor="center",
                                   # orientation="h",
                                   # x=0.5
                                   ),
                               template="plotly_white")

        sex_plot.layout.annotations[0].update(xanchor="left", xshift=-190)
        sex_plot.layout.annotations[1].update(xanchor="left", xshift=-190)
        # sex_plot.update_annotations(xanchor="left", xshift=-190)
        return sex_plot

# def read_total_incidence(total_incidence_data):
#     incidence = pd.read_csv(total_incidence_data)
#     incidence.set_index(["Year", "Sex"], inplace=True)
#     incidence.rename(index={"Males": "Male", "Females": "Female"},
#                      level="Sex", inplace=True)
#     return incidence
#
#
# def read_population_data(population_data, drop_subgroups=True):
#     pop_data = pd.read_csv(population_data, sep=",", usecols=[1, 2, 3, 5])
#     cols = list(pop_data.columns)
#     cols[-1] = "Population"
#     pop_data.columns = cols
#     pop_data["Population"] = pop_data["Population"]*1000
#     if drop_subgroups:
#         pop_data = pop_data.loc[pop_data["Age Group"] == "All ages"]
#         pop_data.drop("Age Group", axis=1, inplace=True)
#         pop_data.set_index(["Year", "Sex"], inplace=True)
#     else:
#         pop_data.set_index(["Year", "Sex", "Age Group"], inplace=True)
#     pop_data.sort_index(inplace=True)
#     pop_data.rename(index={"Both sexes": "Both"}, level="Sex", inplace=True)
#     return pop_data
#
#
# # def aggregate_cancer_age_band(population_data):
#
#
#
# def merge_incidence_and_population_tables(incidence, population):
#     data = pd.merge(incidence, population, left_index=True, right_index=True)
#     data["Relative numbers"] = data["Case numbers"] / data["Population"] * 100000
#     return data
#
#
# def plot_total_incidence(total_incidence_data, raw_count=True):
#     if raw_count:
#         y = "Case numbers"
#         y_title = "Cases per year"
#     else:
#         y = "Relative numbers"
#         y_title = "Cases per 100,000 total population per year"
#     data = total_incidence_data.reset_index()
#     incidence_plot = px.line(data, x="Year", y=y, color="Sex",
#                              markers=True, width=750, height=500,
#                              title=("Total incidence: All invasive cancers "
#                                     "(except NMSC) in Ireland"),
#                              template="plotly_white")
#     incidence_plot.update_layout(yaxis_title=y_title)
#     return incidence_plot


def main(age_incidence_csv, sex_incidence_csv, population_csv, survival_csv):
    age_incidence = AgeIncidenceData.read_csv(age_incidence_csv)
    sex_incidence = SexIncidenceData.read_data(sex_incidence_csv, population_csv)
    survival = SurvivalData.read_csv(survival_csv)

    age_plot = age_incidence.age_incidence.plot(combined=True)
    sex_plot = sex_incidence.sex_incidence.plot(combined=True)
    survival_plot = survival.survival.plot()
    return age_plot, sex_plot, survival_plot
    #
    #
    #
    #
    #
    # # age_incidence_data = read_age_incidence(age_incidence_data)
    # age_incidence_data = AgeIncidence.read_age_incidence(age_incidence_csv)
    # total_incidence_data = read_total_incidence(total_incidence_csv)
    # # survival_data = read_survival(survival_data)
    # survival_data = SurvivalData.read_survival(survival_csv)
    # population_data = read_population_data(population_csv)
    # total_incidence_data = merge_incidence_and_population_tables(total_incidence_data,
    #                                                              population_data)
    #
    # age_incidence_plot = plot_age_incidence(age_incidence_data, raw_count=False)
    # age_raw_incidence_plot = plot_age_incidence(age_incidence_data, raw_count=True)
    # total_incidence_plot = plot_total_incidence(total_incidence_data, raw_count=False)
    # total_raw_incidence_plot = plot_total_incidence(total_incidence_data, raw_count=True)
    # survival_plot = plot_survival(survival_data)
    # return ((age_incidence_data, total_incidence_data, survival_data),
    #         (age_raw_incidence_plot, age_incidence_plot,
    #          total_raw_incidence_plot, total_incidence_plot,
    #          survival_plot))
