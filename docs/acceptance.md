# V1 acceptance evidence

Every SPEC §17 item mapped to the tests or commands that evidence it. `tests/acceptance/test_v1_acceptance.py`
checks that this map covers every item and that every test named here exists, so it cannot drift from the suite.
Run everything with `uv run python scripts/check.py`.

## §17.1 Unit tests

| # | SPEC §17.1 item | Evidence |
|---|---|---|
| 1 | YAML loads and validates valid configuration. | `test_parse_valid_minimal_returns_typed_scenario`, `test_load_example_config_returns_typed_scenario` |
| 2 | Missing fields, duplicate IDs, invalid dates, and invalid percentages are rejected. | `test_missing_required_field_reports_location`, `test_duplicate_ids_rejected`, `test_date_rules_rejected`, `test_out_of_range_values_rejected` |
| 3 | Annual-to-monthly return conversion matches the formula. | `test_monthly_return_rate_compounds_to_annual` |
| 4 | Zero inflation keeps the price index constant. | `test_flat_price_index_is_constant`, `test_stochastic_price_index_zero_inflation_constant` |
| 5 | Inflation-linked income tracks the inflation index. | `test_linked_income_tracks_price_index` |
| 6 | Non-inflation-linked income remains nominally constant. | `test_unlinked_income_is_nominally_constant` |
| 7 | Income starts and ends on configured dates. | `test_income_starts_and_ends_on_configured_dates` |
| 8 | Survivor percentage applies only under the configured recipient-death condition. | `test_survivor_percentage_applies_only_after_recipient_death`, `test_household_stream_survivor_rule` |
| 9 | Spending changes after the first death according to the configured factor. | `test_spending_changes_after_first_death_by_survivor_factor`, `test_survivor_factor_precedence_uses_survivor_then_default` |
| 10 | A dead person never becomes alive again. | `test_dead_person_never_alive_again` |
| 11 | Monthly mortality conversion reproduces the annual probability over twelve identical monthly intervals, within numerical tolerance. | `test_monthly_conversion_reproduces_annual_probability` |
| 12 | Portfolio cash-flow ordering matches the documented convention. | `test_apply_month_orders_return_income_then_spending` |
| 13 | A path records failure at the first month it cannot fund spending. | `test_simulate_paths_records_first_depletion_month` |
| 14 | No negative balance is allowed to compound after failure. | `test_simulate_paths_no_compounding_after_depletion`, `test_apply_month_never_negative` |
| 15 | A fixed seed reproduces outputs. | `test_random_streams_fixed_seed_reproduces_draws`, `test_monte_carlo_fixed_seed_reproduces_outputs`, `test_cli_run_csvs_reproducible` |
| 16 | Common random numbers are reused across candidate budgets and returns. | `test_monte_carlo_reuses_inputs_across_budgets`, `test_optimization_monotone_and_crn`, `test_return_search_monotone_targets_and_crn` |

## §17.2 Integration tests

| # | SPEC §17.2 item | Evidence |
|---|---|---|
| 1 | A zero-spending scenario does not fail from spending depletion. | `test_monte_carlo_zero_spending_never_fails`, `test_simulate_paths_zero_spending_never_depletes` |
| 2 | A scenario with no starting capital and no income fails when positive spending is due. | `test_monte_carlo_no_capital_no_income_fails` |
| 3 | A sufficiently large portfolio with zero spending remains solvent for all completed paths. | `test_monte_carlo_zero_spending_never_fails` |
| 4 | A deterministic mortality fixture produces expected household state transitions. | `test_deterministic_mortality_fixture_state_transitions` |
| 5 | A deterministic inflation fixture produces expected nominal spending. | `test_deterministic_inflation_fixture_expected_nominal_spending` |
| 6 | CSV schemas and units match this specification. | `test_annual_results_csv_format`, `test_lifestyle_results_csv`, `test_sustainability_results_csv` |
| 7 | Censored paths are reported and do not silently count as successes. | `test_censored_paths_never_count_as_success`, `test_cli_run_prints_summary` |
| 8 | Budget optimization returns a feasible budget within configured tolerance on a small deterministic fixture. | `test_optimization_deterministic_fixture_closed_form` |
| 9 | Return optimization either converges to a valid bracketed result or clearly reports no solution. | `test_return_search_deterministic_closed_form`, `test_return_search_reports_bounds` |

## §17.3 Acceptance criteria

| # | SPEC §17.3 criterion | Evidence |
|---|---|---|
| 1 | All required configuration fields are validated. | `test_missing_required_field_reports_location`, `test_strict_scalars_reject_coercion`, `test_inflation_config_rejects_invalid_values` |
| 2 | All unit and integration tests pass. | `check: uv run python scripts/check.py` |
| 3 | A fixed seed and unchanged data/configuration reproduce identical results in the supported environment. | `test_cli_run_csvs_reproducible`, `test_build_run_metadata_reproducible_except_created_at` |
| 4 | Mortality and inflation source files and versions are documented. | `test_data_provenance_hashes_match`, `test_ons_mortality_meta_records_provenance`, `test_uk_cpi_meta_records_provenance` |
| 5 | Annual, sustainability, and lifestyle CSVs are generated with documented schemas. | `test_cli_run_writes_all_outputs`, `test_readme_covers_v1_sections` |
| 6 | Censored paths and Monte Carlo uncertainty are visible in outputs. | `test_cli_run_prints_summary`, `test_annual_results_csv_format`, `test_lifestyle_results_csv` |
| 7 | Budget and return optimization use common random numbers and report convergence. | `test_optimization_monotone_and_crn`, `test_return_search_monotone_targets_and_crn`, `test_optimization_reports_cap` |
| 8 | Tax logic is absent from the core model. | `test_src_has_no_tax_network_or_global_randomness` |
| 9 | The README explains installation, configuration, running the model, output interpretation, assumptions, and limitations. | `test_readme_covers_v1_sections` |

## SPEC §18 decisions

All ten are recorded in `docs/decisions/` and checked by `test_all_spec_18_decisions_recorded`.
