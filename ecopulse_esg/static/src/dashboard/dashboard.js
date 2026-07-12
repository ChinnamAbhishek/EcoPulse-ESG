/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class EcoPulseDashboard extends Component {
    static template = "ecopulse_esg.EcoPulseDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            transactions: 0,
            goals: 0,
            departments: 0,
            factors: 0,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;

        try {
            const results = await Promise.all([
                this.orm.searchCount("ecopulse.carbon.transaction", []),
                this.orm.searchCount("ecopulse.environmental.goal", []),
                this.orm.searchCount("ecopulse.department", []),
                this.orm.searchCount("ecopulse.emission.factor", []),
            ]);

            this.state.transactions = results[0];
            this.state.goals = results[1];
            this.state.departments = results[2];
            this.state.factors = results[3];
        } catch (error) {
            console.error("EcoPulse dashboard error:", error);

            this.notification.add(
                "Dashboard data could not be loaded.",
                {
                    title: "EcoPulse ESG",
                    type: "warning",
                }
            );
        } finally {
            this.state.loading = false;
        }
    }

    refresh() {
        return this.loadData();
    }

    openTransactions() {
        this.action.doAction(
            "ecopulse_esg.action_ecopulse_carbon_transaction"
        );
    }

    openGoals() {
        this.action.doAction(
            "ecopulse_esg.action_ecopulse_environmental_goal"
        );
    }

    openDepartments() {
        this.action.doAction(
            "ecopulse_esg.action_ecopulse_department"
        );
    }

    openFactors() {
        this.action.doAction(
            "ecopulse_esg.action_ecopulse_emission_factor"
        );
    }
}

registry
    .category("actions")
    .add("ecopulse_esg.dashboard", EcoPulseDashboard);
'@ | Set-Content "$root\ecopulse_esg\static\src\dashboard\dashboard.js" -Encoding UTF8
