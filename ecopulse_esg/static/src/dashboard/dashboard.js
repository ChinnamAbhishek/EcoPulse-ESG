/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class EcoPulseDashboard extends Component {
    static template = "ecopulse_esg.EcoPulseDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.allTransactionRecords = [];

        this.state = useState({
            loading: true,
            lastUpdated: "",

            carbonTransactions: 0,
            environmentalGoals: 0,
            departments: 0,
            emissionFactors: 0,

            totalEmissions: 0,
            verifiedTransactions: 0,
            calculatedTransactions: 0,
            draftTransactions: 0,

            scope1Total: 0,
            scope2Total: 0,
            scope3Total: 0,

            scope1Percent: 0,
            scope2Percent: 0,
            scope3Percent: 0,

            recentTransactions: [],

            completedGoals: 0,
            activeGoals: 0,
            atRiskGoals: 0,
            averageGoalProgress: 0,
            goalRecords: [],
            alerts: [],

            monthlyEmissions: [],
            highestEmissionMonth: "No data",
            highestEmissionMonthValue: 0,
            monthlyMaximum: 0,

            departmentRanking: [],
            topDepartment: "No data",
            topDepartmentEmission: 0,
            departmentMaximum: 0,

            sourceAnalytics: [],
            topSource: "No data",
            topSourceEmission: 0,

            departmentOptions: [],

            filters: {
                startDate: "",
                endDate: "",
                departmentId: "",
                scope: "",
                status: "",
            },

            appliedFilters: {
                startDate: "",
                endDate: "",
                departmentId: "",
                scope: "",
                status: "",
            },

            filtersApplied: false,
            filteredTransactionCount: 0,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;

        try {
            const results = await Promise.all([
                this.orm.searchCount(
                    "ecopulse.carbon.transaction",
                    []
                ),

                this.orm.searchCount(
                    "ecopulse.environmental.goal",
                    []
                ),

                this.orm.searchCount(
                    "ecopulse.department",
                    []
                ),

                this.orm.searchCount(
                    "ecopulse.emission.factor",
                    []
                ),

                this.orm.searchRead(
                    "ecopulse.carbon.transaction",
                    [],
                    [
                        "reference",
                        "transaction_date",
                        "department_id",
                        "source_module",
                        "scope",
                        "calculated_emission",
                        "activity_quantity",
                        "activity_unit",
                        "status",
                    ],
                    {
                        limit: 10000,
                        order: "transaction_date asc, id asc",
                    }
                ),

                this.orm.searchRead(
                    "ecopulse.environmental.goal",
                    [],
                    [
                        "name",
                        "department_id",
                        "metric_type",
                        "baseline_value",
                        "target_value",
                        "current_value",
                        "progress_percentage",
                        "status",
                        "risk_level",
                        "start_date",
                        "end_date",
                    ],
                    {
                        limit: 10,
                        order: "end_date asc, id desc",
                    }
                ),

                this.orm.searchRead(
                    "ecopulse.department",
                    [],
                    ["name"],
                    {
                        limit: 1000,
                        order: "name asc",
                    }
                ),
            ]);

            this.state.carbonTransactions = results[0];
            this.state.environmentalGoals = results[1];
            this.state.departments = results[2];
            this.state.emissionFactors = results[3];

            this.allTransactionRecords = results[4];

            const goalRecords = results[5];
            const departmentOptions = results[6];

            this.state.departmentOptions = departmentOptions;

            this.processGoalAnalytics(goalRecords);

            const filteredRecords =
                this.getFilteredTransactions();

            this.processTransactionAnalytics(
                filteredRecords
            );

            this.state.lastUpdated =
                new Date().toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                });
        } catch (error) {
            console.error(
                "EcoPulse dashboard loading error:",
                error
            );

            this.notification.add(
                "Dashboard data could not be loaded.",
                {
                    title: "EcoPulse ESG",
                    type: "danger",
                }
            );
        } finally {
            this.state.loading = false;
        }
    }

    processTransactionAnalytics(transactionRecords) {
        let totalEmissions = 0;

        let scope1Total = 0;
        let scope2Total = 0;
        let scope3Total = 0;

        let verifiedTransactions = 0;
        let calculatedTransactions = 0;
        let draftTransactions = 0;

        const monthlyMap = {};
        const departmentMap = {};
        const sourceMap = {};

        const activeRecords = transactionRecords.filter(
            (transaction) => {
                return transaction.status !== "cancelled";
            }
        );

        for (const transaction of activeRecords) {
            const emission = Number(
                transaction.calculated_emission || 0
            );

            totalEmissions += emission;

            if (transaction.scope === "scope_1") {
                scope1Total += emission;
            } else if (transaction.scope === "scope_2") {
                scope2Total += emission;
            } else if (transaction.scope === "scope_3") {
                scope3Total += emission;
            }

            if (transaction.status === "verified") {
                verifiedTransactions += 1;
            } else if (
                transaction.status === "calculated"
            ) {
                calculatedTransactions += 1;
            } else if (transaction.status === "draft") {
                draftTransactions += 1;
            }

            this.addMonthlyEmission(
                monthlyMap,
                transaction.transaction_date,
                emission
            );

            this.addDepartmentEmission(
                departmentMap,
                transaction.department_id,
                emission
            );

            this.addSourceEmission(
                sourceMap,
                transaction.source_module,
                emission
            );
        }

        const monthlyEmissions =
            this.prepareMonthlyAnalytics(monthlyMap);

        const departmentRanking =
            this.prepareDepartmentRanking(
                departmentMap
            );

        const sourceAnalytics =
            this.prepareSourceAnalytics(sourceMap);

        const highestMonth =
            monthlyEmissions.reduce(
                (highest, month) => {
                    if (
                        !highest ||
                        month.total > highest.total
                    ) {
                        return month;
                    }

                    return highest;
                },
                null
            );

        const topDepartment =
            departmentRanking.length > 0
                ? departmentRanking[0]
                : null;

        const topSource =
            sourceAnalytics.length > 0
                ? sourceAnalytics[0]
                : null;

        this.state.filteredTransactionCount =
            transactionRecords.length;

        this.state.totalEmissions =
            totalEmissions;

        this.state.verifiedTransactions =
            verifiedTransactions;

        this.state.calculatedTransactions =
            calculatedTransactions;

        this.state.draftTransactions =
            draftTransactions;

        this.state.scope1Total = scope1Total;
        this.state.scope2Total = scope2Total;
        this.state.scope3Total = scope3Total;

        if (totalEmissions > 0) {
            this.state.scope1Percent =
                Math.round(
                    (scope1Total / totalEmissions) * 100
                );

            this.state.scope2Percent =
                Math.round(
                    (scope2Total / totalEmissions) * 100
                );

            this.state.scope3Percent =
                Math.max(
                    0,
                    100 -
                        this.state.scope1Percent -
                        this.state.scope2Percent
                );
        } else {
            this.state.scope1Percent = 0;
            this.state.scope2Percent = 0;
            this.state.scope3Percent = 0;
        }

        this.state.monthlyEmissions =
            monthlyEmissions;

        this.state.monthlyMaximum =
            highestMonth
                ? highestMonth.total
                : 0;

        this.state.highestEmissionMonth =
            highestMonth
                ? highestMonth.label
                : "No data";

        this.state.highestEmissionMonthValue =
            highestMonth
                ? highestMonth.total
                : 0;

        this.state.departmentRanking =
            departmentRanking;

        this.state.departmentMaximum =
            topDepartment
                ? topDepartment.total
                : 0;

        this.state.topDepartment =
            topDepartment
                ? topDepartment.name
                : "No data";

        this.state.topDepartmentEmission =
            topDepartment
                ? topDepartment.total
                : 0;

        this.state.sourceAnalytics =
            sourceAnalytics;

        this.state.topSource =
            topSource
                ? topSource.label
                : "No data";

        this.state.topSourceEmission =
            topSource
                ? topSource.total
                : 0;

        this.state.recentTransactions = [
            ...transactionRecords,
        ]
            .sort((first, second) => {
                const firstDate =
                    first.transaction_date || "";

                const secondDate =
                    second.transaction_date || "";

                if (firstDate === secondDate) {
                    return second.id - first.id;
                }

                return secondDate.localeCompare(
                    firstDate
                );
            })
            .slice(0, 8);
    }

    processGoalAnalytics(goalRecords) {
        let completedGoals = 0;
        let activeGoals = 0;
        let atRiskGoals = 0;
        let totalGoalProgress = 0;

        const alerts = [];

        for (const goal of goalRecords) {
            const progress = Number(
                goal.progress_percentage || 0
            );

            totalGoalProgress += progress;

            if (goal.status === "completed") {
                completedGoals += 1;
            } else if (
                goal.status === "at_risk"
            ) {
                atRiskGoals += 1;
            } else if (
                goal.status === "active"
            ) {
                activeGoals += 1;
            }

            if (
                goal.status === "at_risk" ||
                goal.risk_level === "high"
            ) {
                alerts.push({
                    id: goal.id,
                    title: goal.name,
                    message:
                        "This goal requires immediate attention.",
                    level: "high",
                });
            } else if (
                goal.risk_level === "medium"
            ) {
                alerts.push({
                    id: goal.id,
                    title: goal.name,
                    message:
                        "Progress is below the expected level.",
                    level: "medium",
                });
            }
        }

        this.state.completedGoals =
            completedGoals;

        this.state.activeGoals =
            activeGoals;

        this.state.atRiskGoals =
            atRiskGoals;

        this.state.averageGoalProgress =
            goalRecords.length
                ? Math.round(
                      totalGoalProgress /
                          goalRecords.length
                  )
                : 0;

        this.state.goalRecords =
            goalRecords;

        this.state.alerts =
            alerts.slice(0, 6);
    }

    getFilteredTransactions() {
        const filters =
            this.state.appliedFilters;

        return this.allTransactionRecords.filter(
            (transaction) => {
                const transactionDate =
                    transaction.transaction_date ||
                    "";

                const departmentId =
                    Array.isArray(
                        transaction.department_id
                    ) &&
                    transaction.department_id.length
                        ? String(
                              transaction.department_id[0]
                          )
                        : "";

                if (
                    filters.startDate &&
                    transactionDate <
                        filters.startDate
                ) {
                    return false;
                }

                if (
                    filters.endDate &&
                    transactionDate >
                        filters.endDate
                ) {
                    return false;
                }

                if (
                    filters.departmentId &&
                    departmentId !==
                        String(filters.departmentId)
                ) {
                    return false;
                }

                if (
                    filters.scope &&
                    transaction.scope !==
                        filters.scope
                ) {
                    return false;
                }

                if (
                    filters.status &&
                    transaction.status !==
                        filters.status
                ) {
                    return false;
                }

                return true;
            }
        );
    }

    applyFilters() {
        const startDate =
            this.state.filters.startDate || "";

        const endDate =
            this.state.filters.endDate || "";

        if (
            startDate &&
            endDate &&
            startDate > endDate
        ) {
            this.notification.add(
                "Start date cannot be later than end date.",
                {
                    title: "Invalid Date Range",
                    type: "warning",
                }
            );

            return;
        }

        this.state.appliedFilters.startDate =
            this.state.filters.startDate;

        this.state.appliedFilters.endDate =
            this.state.filters.endDate;

        this.state.appliedFilters.departmentId =
            this.state.filters.departmentId;

        this.state.appliedFilters.scope =
            this.state.filters.scope;

        this.state.appliedFilters.status =
            this.state.filters.status;

        this.state.filtersApplied =
            this.hasActiveFilters();

        const filteredRecords =
            this.getFilteredTransactions();

        this.processTransactionAnalytics(
            filteredRecords
        );

        this.state.lastUpdated =
            new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });

        this.notification.add(
            `${filteredRecords.length} transaction records matched the selected filters.`,
            {
                title: "Filters Applied",
                type: "success",
            }
        );
    }

    resetFilters() {
        this.state.filters.startDate = "";
        this.state.filters.endDate = "";
        this.state.filters.departmentId = "";
        this.state.filters.scope = "";
        this.state.filters.status = "";

        this.state.appliedFilters.startDate = "";
        this.state.appliedFilters.endDate = "";
        this.state.appliedFilters.departmentId = "";
        this.state.appliedFilters.scope = "";
        this.state.appliedFilters.status = "";

        this.state.filtersApplied = false;

        this.processTransactionAnalytics(
            this.allTransactionRecords
        );

        this.state.lastUpdated =
            new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });

        this.notification.add(
            "Dashboard filters have been reset.",
            {
                title: "Filters Reset",
                type: "info",
            }
        );
    }

    hasActiveFilters() {
        return Boolean(
            this.state.appliedFilters.startDate ||
            this.state.appliedFilters.endDate ||
            this.state.appliedFilters.departmentId ||
            this.state.appliedFilters.scope ||
            this.state.appliedFilters.status
        );
    }

    exportFilteredTransactions() {
        const records =
            this.getFilteredTransactions();

        if (!records.length) {
            this.notification.add(
                "No transaction records are available to export.",
                {
                    title: "CSV Export",
                    type: "warning",
                }
            );

            return;
        }

        const headings = [
            "Reference",
            "Transaction Date",
            "Department",
            "Source Module",
            "Scope",
            "Activity Quantity",
            "Activity Unit",
            "Calculated Emission (kg CO2e)",
            "Status",
        ];

        const rows = records.map(
            (transaction) => {
                return [
                    transaction.reference || "",
                    transaction.transaction_date || "",
                    this.getDepartmentName(
                        transaction.department_id
                    ),
                    this.getSourceLabel(
                        transaction.source_module
                    ),
                    this.getScopeLabel(
                        transaction.scope
                    ),
                    transaction.activity_quantity || 0,
                    transaction.activity_unit || "",
                    transaction.calculated_emission || 0,
                    this.getStatusLabel(
                        transaction.status
                    ),
                ];
            }
        );

        const csvRows = [
            headings,
            ...rows,
        ].map((row) => {
            return row
                .map((value) => {
                    return this.escapeCsvValue(
                        value
                    );
                })
                .join(",");
        });

        const csvContent =
            "\uFEFF" +
            csvRows.join("\r\n");

        const blob = new Blob(
            [csvContent],
            {
                type: "text/csv;charset=utf-8;",
            }
        );

        const downloadUrl =
            window.URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        const timestamp = new Date()
            .toISOString()
            .slice(0, 19)
            .replace(/:/g, "-");

        link.href = downloadUrl;

        link.download =
            `ecopulse-carbon-transactions-${timestamp}.csv`;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        window.URL.revokeObjectURL(
            downloadUrl
        );

        this.notification.add(
            `${records.length} transaction records exported successfully.`,
            {
                title: "CSV Export Complete",
                type: "success",
            }
        );
    }

    escapeCsvValue(value) {
        const stringValue =
            String(value ?? "");

        return `"${stringValue.replace(
            /"/g,
            '""'
        )}"`;
    }

    addMonthlyEmission(
        monthlyMap,
        dateValue,
        emission
    ) {
        if (!dateValue) {
            return;
        }

        const date =
            new Date(
                `${dateValue}T00:00:00`
            );

        if (
            Number.isNaN(date.getTime())
        ) {
            return;
        }

        const year =
            date.getFullYear();

        const month = String(
            date.getMonth() + 1
        ).padStart(2, "0");

        const key =
            `${year}-${month}`;

        if (!monthlyMap[key]) {
            monthlyMap[key] = {
                key,
                year,
                month: Number(month),
                total: 0,
            };
        }

        monthlyMap[key].total +=
            emission;
    }

    prepareMonthlyAnalytics(monthlyMap) {
        const records =
            Object.values(monthlyMap)
                .sort((first, second) => {
                    return first.key.localeCompare(
                        second.key
                    );
                })
                .slice(-12);

        return records.map((record) => {
            const date = new Date(
                record.year,
                record.month - 1,
                1
            );

            return {
                key: record.key,

                label:
                    date.toLocaleDateString(
                        "en-IN",
                        {
                            month: "short",
                            year: "numeric",
                        }
                    ),

                shortLabel:
                    date.toLocaleDateString(
                        "en-IN",
                        {
                            month: "short",
                        }
                    ),

                total: Number(
                    record.total.toFixed(2)
                ),
            };
        });
    }

    addDepartmentEmission(
        departmentMap,
        department,
        emission
    ) {
        const departmentId =
            Array.isArray(department) &&
            department.length
                ? department[0]
                : 0;

        const departmentName =
            Array.isArray(department) &&
            department.length > 1
                ? department[1]
                : "Not Assigned";

        const key =
            String(departmentId);

        if (!departmentMap[key]) {
            departmentMap[key] = {
                id: departmentId,
                name: departmentName,
                total: 0,
                transactions: 0,
            };
        }

        departmentMap[key].total +=
            emission;

        departmentMap[key]
            .transactions += 1;
    }

    prepareDepartmentRanking(
        departmentMap
    ) {
        return Object.values(
            departmentMap
        )
            .sort((first, second) => {
                return (
                    second.total -
                    first.total
                );
            })
            .slice(0, 8)
            .map(
                (department, index) => {
                    return {
                        ...department,
                        rank: index + 1,
                        total: Number(
                            department.total.toFixed(
                                2
                            )
                        ),
                    };
                }
            );
    }

    addSourceEmission(
        sourceMap,
        source,
        emission
    ) {
        const key =
            source || "manual";

        if (!sourceMap[key]) {
            sourceMap[key] = {
                key,
                label:
                    this.getSourceLabel(
                        key
                    ),
                total: 0,
                transactions: 0,
            };
        }

        sourceMap[key].total +=
            emission;

        sourceMap[key]
            .transactions += 1;
    }

    prepareSourceAnalytics(
        sourceMap
    ) {
        return Object.values(sourceMap)
            .sort((first, second) => {
                return (
                    second.total -
                    first.total
                );
            })
            .map((source) => {
                return {
                    ...source,
                    total: Number(
                        source.total.toFixed(2)
                    ),
                };
            });
    }

    getMonthlyBarHeight(total) {
        const maximum = Number(
            this.state.monthlyMaximum || 0
        );

        if (maximum <= 0) {
            return 4;
        }

        return Math.max(
            4,
            Math.round(
                (Number(total || 0) /
                    maximum) *
                    100
            )
        );
    }

    getDepartmentBarWidth(total) {
        const maximum = Number(
            this.state.departmentMaximum || 0
        );

        if (maximum <= 0) {
            return 0;
        }

        return Math.max(
            2,
            Math.round(
                (Number(total || 0) /
                    maximum) *
                    100
            )
        );
    }

    async refreshDashboard() {
        await this.loadDashboardData();

        this.notification.add(
            "Dashboard refreshed successfully.",
            {
                title: "EcoPulse ESG",
                type: "success",
            }
        );
    }

    formatNumber(value) {
        return new Intl.NumberFormat(
            "en-IN",
            {
                maximumFractionDigits: 2,
            }
        ).format(Number(value || 0));
    }

    getDepartmentName(department) {
        if (
            Array.isArray(department) &&
            department.length > 1
        ) {
            return department[1];
        }

        return "Not Assigned";
    }

    getScopeLabel(scope) {
        const labels = {
            scope_1: "Scope 1",
            scope_2: "Scope 2",
            scope_3: "Scope 3",
        };

        return (
            labels[scope] ||
            "Unspecified"
        );
    }

    getStatusLabel(status) {
        const labels = {
            draft: "Draft",
            calculated: "Calculated",
            verified: "Verified",
            cancelled: "Cancelled",
        };

        return (
            labels[status] ||
            "Unknown"
        );
    }

    getStatusClass(status) {
        const classes = {
            draft: "eco_status_draft",
            calculated:
                "eco_status_calculated",
            verified:
                "eco_status_verified",
            cancelled:
                "eco_status_cancelled",
        };

        return (
            classes[status] ||
            "eco_status_draft"
        );
    }

    getSourceLabel(source) {
        const labels = {
            purchase: "Purchase",
            fleet: "Fleet",
            manufacturing:
                "Manufacturing",
            expense: "Expense",
            electricity: "Electricity",
            travel: "Travel",
            waste: "Waste",
            manual: "Manual",
        };

        return (
            labels[source] ||
            "Manual"
        );
    }

    getSourceIcon(source) {
        const icons = {
            purchase:
                "fa-shopping-cart",
            fleet: "fa-truck",
            manufacturing:
                "fa-industry",
            expense: "fa-money",
            electricity: "fa-bolt",
            travel: "fa-plane",
            waste: "fa-trash",
            manual: "fa-pencil",
        };

        return (
            icons[source] ||
            "fa-leaf"
        );
    }

    getGoalStatusLabel(status) {
        const labels = {
            draft: "Draft",
            active: "Active",
            completed: "Completed",
            at_risk: "At Risk",
            cancelled: "Cancelled",
        };

        return (
            labels[status] ||
            "Unknown"
        );
    }

    getGoalStatusClass(status) {
        const classes = {
            draft: "eco_goal_draft",
            active: "eco_goal_active",
            completed:
                "eco_goal_completed",
            at_risk: "eco_goal_risk",
            cancelled:
                "eco_goal_cancelled",
        };

        return (
            classes[status] ||
            "eco_goal_draft"
        );
    }

    getRiskClass(level) {
        const classes = {
            low: "eco_alert_low",
            medium:
                "eco_alert_medium",
            high: "eco_alert_high",
        };

        return (
            classes[level] ||
            "eco_alert_low"
        );
    }

    getMetricLabel(metric) {
        const labels = {
            emission_reduction:
                "Emission Reduction",

            renewable_energy:
                "Renewable Energy",

            waste_reduction:
                "Waste Reduction",

            water_conservation:
                "Water Conservation",

            energy_efficiency:
                "Energy Efficiency",

            other: "Other",
        };

        return (
            labels[metric] ||
            "Other"
        );
    }

    openCarbonTransactions() {
        return this.actionService.doAction(
            "ecopulse_esg.action_ecopulse_carbon_transaction"
        );
    }

    openEnvironmentalGoals() {
        return this.actionService.doAction(
            "ecopulse_esg.action_ecopulse_environmental_goal"
        );
    }

    openDepartments() {
        return this.actionService.doAction(
            "ecopulse_esg.action_ecopulse_department"
        );
    }

    openEmissionFactors() {
        return this.actionService.doAction(
            "ecopulse_esg.action_ecopulse_emission_factor"
        );
    }

    openESGReportWizard() {
        return this.actionService.doAction(
            "ecopulse_esg.action_ecopulse_esg_report_wizard"
        );
    }

    createCarbonTransaction() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "New Carbon Transaction",
            res_model:
                "ecopulse.carbon.transaction",
            views: [[false, "form"]],
            target: "current",
        });
    }

    createEnvironmentalGoal() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name:
                "New Environmental Goal",
            res_model:
                "ecopulse.environmental.goal",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry
    .category("actions")
    .add(
        "ecopulse_esg.dashboard",
        EcoPulseDashboard
    );