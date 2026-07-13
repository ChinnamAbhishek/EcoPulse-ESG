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

        this.state = useState({
            loading: true,
            lastUpdated: "",
            carbonTransactions: 0,
            environmentalGoals: 0,
            departments: 0,
            emissionFactors: 0,
            totalEmissions: 0,
            scope1Total: 0,
            scope2Total: 0,
            scope3Total: 0,
            scope1Percent: 0,
            scope2Percent: 0,
            scope3Percent: 0,
            recentTransactions: [],
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
                    ["carbon_emission", "scope"],
                    {
                        limit: 5000,
                    }
                ),
                this.orm.searchRead(
                    "ecopulse.carbon.transaction",
                    [],
                    [
                        "reference",
                        "transaction_date",
                        "department_id",
                        "scope",
                        "carbon_emission",
                        "status",
                    ],
                    {
                        limit: 6,
                        order: "transaction_date desc, id desc",
                    }
                ),
            ]);

            const carbonTransactions = results[0];
            const environmentalGoals = results[1];
            const departments = results[2];
            const emissionFactors = results[3];
            const transactionRecords = results[4];
            const recentTransactions = results[5];

            let totalEmissions = 0;
            let scope1Total = 0;
            let scope2Total = 0;
            let scope3Total = 0;

            for (const transaction of transactionRecords) {
                const emission = Number(
                    transaction.carbon_emission || 0
                );

                totalEmissions += emission;

                if (transaction.scope === "scope_1") {
                    scope1Total += emission;
                } else if (transaction.scope === "scope_2") {
                    scope2Total += emission;
                } else if (transaction.scope === "scope_3") {
                    scope3Total += emission;
                }
            }

            this.state.carbonTransactions = carbonTransactions;
            this.state.environmentalGoals = environmentalGoals;
            this.state.departments = departments;
            this.state.emissionFactors = emissionFactors;
            this.state.totalEmissions = totalEmissions;
            this.state.scope1Total = scope1Total;
            this.state.scope2Total = scope2Total;
            this.state.scope3Total = scope3Total;

            if (totalEmissions > 0) {
                this.state.scope1Percent = Math.round(
                    (scope1Total / totalEmissions) * 100
                );

                this.state.scope2Percent = Math.round(
                    (scope2Total / totalEmissions) * 100
                );

                this.state.scope3Percent = Math.max(
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

            this.state.recentTransactions = recentTransactions;

            this.state.lastUpdated = new Date().toLocaleTimeString(
                [],
                {
                    hour: "2-digit",
                    minute: "2-digit",
                }
            );
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
        return new Intl.NumberFormat("en-IN", {
            maximumFractionDigits: 2,
        }).format(Number(value || 0));
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

        return labels[scope] || "Unspecified";
    }

    getStatusLabel(status) {
        if (!status) {
            return "Draft";
        }

        return status
            .split("_")
            .map((word) => {
                return (
                    word.charAt(0).toUpperCase() +
                    word.slice(1)
                );
            })
            .join(" ");
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

    createCarbonTransaction() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "New Carbon Transaction",
            res_model: "ecopulse.carbon.transaction",
            views: [[false, "form"]],
            target: "current",
        });
    }

    createEnvironmentalGoal() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "New Environmental Goal",
            res_model: "ecopulse.environmental.goal",
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