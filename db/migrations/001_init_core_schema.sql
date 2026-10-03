BEGIN;

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    jurisdiction CHAR(2),
    country_code CHAR(2),
    sector TEXT,
    industry TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT companies_legal_name_nonempty CHECK (length(btrim(legal_name)) > 0),
    CONSTRAINT companies_display_name_nonempty CHECK (length(btrim(display_name)) > 0)
);
CREATE INDEX idx_companies_display_name ON companies (lower(display_name));
CREATE INDEX idx_companies_jurisdiction ON companies (jurisdiction);
CREATE INDEX idx_companies_sector_industry ON companies (sector, industry);

CREATE TABLE source_systems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    base_url TEXT,
    documentation_url TEXT,
    license_terms_url TEXT,
    rate_limit_per_minute INTEGER,
    rate_limit_per_day INTEGER,
    supported_countries CHAR(2)[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT source_systems_name_nonempty CHECK (length(btrim(name)) > 0),
    CONSTRAINT source_systems_type_nonempty CHECK (length(btrim(source_type)) > 0),
    CONSTRAINT source_systems_rate_limit_minute_positive
        CHECK (rate_limit_per_minute IS NULL OR rate_limit_per_minute > 0),
    CONSTRAINT source_systems_rate_limit_day_positive
        CHECK (rate_limit_per_day IS NULL OR rate_limit_per_day > 0)
);
CREATE INDEX idx_source_systems_type ON source_systems (source_type);
CREATE INDEX idx_source_systems_active ON source_systems (is_active);

CREATE TABLE company_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    source_system_id UUID REFERENCES source_systems(id) ON DELETE RESTRICT,
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    namespace TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from DATE,
    valid_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT company_identifiers_type_nonempty CHECK (length(btrim(identifier_type)) > 0),
    CONSTRAINT company_identifiers_value_nonempty CHECK (length(btrim(identifier_value)) > 0),
    CONSTRAINT company_identifiers_namespace_nonempty CHECK (length(btrim(namespace)) > 0),
    CONSTRAINT company_identifiers_valid_range
        CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);
CREATE UNIQUE INDEX uq_company_identifiers_namespace_value
    ON company_identifiers (namespace, identifier_type, normalized_value);
CREATE UNIQUE INDEX uq_company_identifiers_primary
    ON company_identifiers (company_id, namespace, identifier_type)
    WHERE is_primary;
CREATE INDEX idx_company_identifiers_company ON company_identifiers (company_id);
CREATE INDEX idx_company_identifiers_source ON company_identifiers (source_system_id);

CREATE TABLE securities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    ticker TEXT,
    exchange_code TEXT,
    exchange_country_code CHAR(2),
    isin CHAR(12),
    currency CHAR(3),
    security_type TEXT,
    listing_status TEXT NOT NULL DEFAULT 'ACTIVE',
    first_listing_date DATE,
    delisting_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT securities_listing_status_valid
        CHECK (listing_status IN ('ACTIVE', 'DELISTED', 'SUSPENDED', 'UNKNOWN')),
    CONSTRAINT securities_ticker_nonempty CHECK (ticker IS NULL OR length(btrim(ticker)) > 0),
    CONSTRAINT securities_exchange_nonempty
        CHECK (exchange_code IS NULL OR length(btrim(exchange_code)) > 0),
    CONSTRAINT securities_currency_format
        CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$'),
    CONSTRAINT securities_listing_dates_valid
        CHECK (delisting_date IS NULL OR first_listing_date IS NULL
               OR delisting_date >= first_listing_date)
);
CREATE UNIQUE INDEX uq_securities_exchange_ticker
    ON securities (upper(exchange_code), upper(ticker))
    WHERE listing_status = 'ACTIVE'
      AND exchange_code IS NOT NULL AND ticker IS NOT NULL;
CREATE UNIQUE INDEX uq_securities_isin ON securities (isin) WHERE isin IS NOT NULL;
CREATE INDEX idx_securities_company ON securities (company_id);
CREATE INDEX idx_securities_ticker ON securities (upper(ticker)) WHERE ticker IS NOT NULL;

CREATE TABLE filings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    source_system_id UUID NOT NULL REFERENCES source_systems(id) ON DELETE RESTRICT,
    filing_type TEXT NOT NULL,
    filing_code TEXT,
    accession_number TEXT,
    document_title TEXT,
    document_reference TEXT NOT NULL,
    filing_date DATE,
    period_start DATE,
    period_end DATE,
    published_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    restates_filing_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT filings_type_nonempty CHECK (length(btrim(filing_type)) > 0),
    CONSTRAINT filings_document_reference_nonempty
        CHECK (length(btrim(document_reference)) > 0),
    CONSTRAINT filings_period_valid
        CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start),
    CONSTRAINT filings_id_company_source_unique UNIQUE (id, company_id, source_system_id),
    CONSTRAINT filings_restates_fk
        FOREIGN KEY (restates_filing_id, company_id, source_system_id)
        REFERENCES filings(id, company_id, source_system_id) ON DELETE RESTRICT,
    CONSTRAINT filings_not_own_restatement CHECK (restates_filing_id IS NULL OR restates_filing_id <> id)
);
CREATE UNIQUE INDEX uq_filings_accession
    ON filings (source_system_id, accession_number)
    WHERE accession_number IS NOT NULL;
CREATE INDEX idx_filings_company_period ON filings (company_id, period_end DESC);
CREATE INDEX idx_filings_source_published ON filings (source_system_id, published_at DESC);
CREATE INDEX idx_filings_retrieved_at ON filings (retrieved_at);
CREATE INDEX idx_filings_restates ON filings (restates_filing_id);

CREATE TABLE source_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system_id UUID NOT NULL REFERENCES source_systems(id) ON DELETE RESTRICT,
    company_id UUID REFERENCES companies(id) ON DELETE RESTRICT,
    filing_id UUID,
    retrieval_batch_id UUID NOT NULL,
    observation_kind TEXT NOT NULL,
    source_record_id TEXT,
    source_record_hash TEXT NOT NULL,
    source_document_reference TEXT,
    provider_payload JSONB,
    payload_storage_reference TEXT,
    published_at TIMESTAMPTZ,
    effective_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT source_observations_kind_nonempty
        CHECK (length(btrim(observation_kind)) > 0),
    CONSTRAINT source_observations_hash_sha256
        CHECK (source_record_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT source_observations_payload_retained
        CHECK (provider_payload IS NOT NULL OR payload_storage_reference IS NOT NULL),
    CONSTRAINT source_observations_filing_requires_company CHECK
        (filing_id IS NULL OR company_id IS NOT NULL),
    CONSTRAINT source_observations_id_company_unique UNIQUE (id, company_id),
    CONSTRAINT source_observations_filing_fk
        FOREIGN KEY (filing_id, company_id, source_system_id)
        REFERENCES filings(id, company_id, source_system_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX uq_source_observations_record_per_retrieval
    ON source_observations (source_system_id, source_record_id, retrieved_at)
    WHERE source_record_id IS NOT NULL;
CREATE INDEX idx_source_observations_company_retrieved
    ON source_observations (company_id, retrieved_at DESC);
CREATE INDEX idx_source_observations_source_kind
    ON source_observations (source_system_id, observation_kind);
CREATE INDEX idx_source_observations_filing ON source_observations (filing_id);
CREATE INDEX idx_source_observations_batch ON source_observations (retrieval_batch_id);

CREATE TABLE normalization_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    normalizer_name TEXT NOT NULL,
    normalization_version TEXT NOT NULL,
    code_revision TEXT,
    run_status TEXT NOT NULL DEFAULT 'RUNNING',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT normalization_runs_name_nonempty
        CHECK (length(btrim(normalizer_name)) > 0),
    CONSTRAINT normalization_runs_version_nonempty
        CHECK (length(btrim(normalization_version)) > 0),
    CONSTRAINT normalization_runs_status_valid
        CHECK (run_status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    CONSTRAINT normalization_runs_completion_valid
        CHECK ((run_status = 'RUNNING' AND completed_at IS NULL)
            OR (run_status IN ('COMPLETED', 'FAILED') AND completed_at IS NOT NULL))
);
CREATE INDEX idx_normalization_runs_status_started
    ON normalization_runs (run_status, started_at DESC);
CREATE INDEX idx_normalization_runs_version ON normalization_runs (normalization_version);

CREATE TABLE normalization_run_observations (
    normalization_run_id UUID NOT NULL
        REFERENCES normalization_runs(id) ON DELETE RESTRICT,
    source_observation_id UUID NOT NULL
        REFERENCES source_observations(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (normalization_run_id, source_observation_id)
);
CREATE INDEX idx_normalization_run_observations_observation
    ON normalization_run_observations (source_observation_id);

CREATE TABLE metric_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_key TEXT NOT NULL,
    definition_version INTEGER NOT NULL,
    supersedes_metric_definition_id UUID,
    display_name TEXT NOT NULL,
    metric_group TEXT NOT NULL,
    unit_dimension TEXT NOT NULL,
    unit_code TEXT,
    currency_requirement TEXT NOT NULL DEFAULT 'OPTIONAL',
    period_requirement TEXT NOT NULL DEFAULT 'OPTIONAL',
    statement_context TEXT,
    accounting_basis TEXT,
    consolidation_scope TEXT,
    definition_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT metric_definitions_key_nonempty CHECK (length(btrim(metric_key)) > 0),
    CONSTRAINT metric_definitions_name_nonempty CHECK (length(btrim(display_name)) > 0),
    CONSTRAINT metric_definitions_group_nonempty CHECK (length(btrim(metric_group)) > 0),
    CONSTRAINT metric_definitions_dimension_nonempty CHECK (length(btrim(unit_dimension)) > 0),
    CONSTRAINT metric_definitions_description_nonempty
        CHECK (length(btrim(description)) > 0),
    CONSTRAINT metric_definitions_version_positive CHECK (definition_version > 0),
    CONSTRAINT metric_definitions_key_version_unique UNIQUE (metric_key, definition_version),
    CONSTRAINT metric_definitions_supersedes_fk
        FOREIGN KEY (supersedes_metric_definition_id)
        REFERENCES metric_definitions(id) ON DELETE RESTRICT,
    CONSTRAINT metric_definitions_not_self_superseding
        CHECK (supersedes_metric_definition_id IS NULL
               OR supersedes_metric_definition_id <> id),
    CONSTRAINT metric_definitions_currency_requirement_valid
        CHECK (currency_requirement IN ('REQUIRED', 'OPTIONAL', 'NOT_APPLICABLE')),
    CONSTRAINT metric_definitions_period_requirement_valid
        CHECK (period_requirement IN ('REQUIRED', 'OPTIONAL', 'NOT_APPLICABLE'))
);
CREATE INDEX idx_metric_definitions_group ON metric_definitions (metric_group);
CREATE INDEX idx_metric_definitions_context
    ON metric_definitions (statement_context, accounting_basis, consolidation_scope);
CREATE INDEX idx_metric_definitions_supersedes
    ON metric_definitions (supersedes_metric_definition_id);

CREATE TABLE source_metric_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system_id UUID NOT NULL REFERENCES source_systems(id) ON DELETE RESTRICT,
    metric_definition_id UUID NOT NULL REFERENCES metric_definitions(id) ON DELETE RESTRICT,
    source_metric_code TEXT NOT NULL,
    source_context_key TEXT NOT NULL DEFAULT '',
    mapping_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT source_metric_mappings_code_nonempty
        CHECK (length(btrim(source_metric_code)) > 0),
    CONSTRAINT source_metric_mappings_unique
        UNIQUE (source_system_id, source_metric_code, source_context_key)
);
CREATE INDEX idx_source_metric_mappings_metric ON source_metric_mappings (metric_definition_id);

CREATE TABLE financial_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    metric_definition_id UUID NOT NULL REFERENCES metric_definitions(id) ON DELETE RESTRICT,
    normalization_run_id UUID NOT NULL
        REFERENCES normalization_runs(id) ON DELETE RESTRICT,
    series_key TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    supersedes_fact_id UUID,
    value NUMERIC NOT NULL,
    unit_code TEXT NOT NULL,
    currency CHAR(3),
    period_start DATE,
    period_end DATE,
    period_type TEXT NOT NULL,
    effective_at TIMESTAMPTZ,
    data_type TEXT NOT NULL,
    confidence NUMERIC(5, 4),
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT financial_facts_series_nonempty CHECK (length(btrim(series_key)) > 0),
    CONSTRAINT financial_facts_version_positive CHECK (version_number > 0),
    CONSTRAINT financial_facts_unit_nonempty CHECK (length(btrim(unit_code)) > 0),
    CONSTRAINT financial_facts_period_type_valid
        CHECK (period_type IN ('ANNUAL', 'QUARTERLY', 'TTM', 'INSTANT', 'OTHER')),
    CONSTRAINT financial_facts_data_type_valid
        CHECK (data_type IN ('REPORTED', 'DERIVED', 'ASSUMPTION', 'ESTIMATE')),
    CONSTRAINT financial_facts_confidence_range
        CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT financial_facts_period_valid
        CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start),
    CONSTRAINT financial_facts_id_company_unique UNIQUE (id, company_id),
    CONSTRAINT financial_facts_id_company_run_unique
        UNIQUE (id, company_id, normalization_run_id),
    CONSTRAINT financial_facts_version_unique
        UNIQUE (company_id, metric_definition_id, series_key, version_number),
    CONSTRAINT financial_facts_supersedes_fk
        FOREIGN KEY (supersedes_fact_id, company_id)
        REFERENCES financial_facts(id, company_id) ON DELETE RESTRICT,
    CONSTRAINT financial_facts_not_self_superseding
        CHECK (supersedes_fact_id IS NULL OR supersedes_fact_id <> id)
);
CREATE INDEX idx_financial_facts_company_metric_period
    ON financial_facts (company_id, metric_definition_id, period_end DESC);
CREATE INDEX idx_financial_facts_metric ON financial_facts (metric_definition_id);
CREATE INDEX idx_financial_facts_normalization_run ON financial_facts (normalization_run_id);
CREATE INDEX idx_financial_facts_supersedes ON financial_facts (supersedes_fact_id);
CREATE INDEX idx_financial_facts_type ON financial_facts (data_type);

ALTER TABLE securities ADD CONSTRAINT securities_id_company_unique UNIQUE (id, company_id);

CREATE TABLE fact_source_observations (
    financial_fact_id UUID NOT NULL,
    source_observation_id UUID NOT NULL,
    normalization_run_id UUID NOT NULL,
    company_id UUID NOT NULL,
    support_role TEXT NOT NULL DEFAULT 'SUPPORTING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (financial_fact_id, source_observation_id),
    CONSTRAINT fact_source_observations_role_nonempty
        CHECK (length(btrim(support_role)) > 0),
    CONSTRAINT fact_source_observations_fact_fk
        FOREIGN KEY (financial_fact_id, company_id, normalization_run_id)
        REFERENCES financial_facts(id, company_id, normalization_run_id) ON DELETE RESTRICT,
    CONSTRAINT fact_source_observations_observation_fk
        FOREIGN KEY (source_observation_id, company_id)
        REFERENCES source_observations(id, company_id) ON DELETE RESTRICT,
    CONSTRAINT fact_source_observations_run_input_fk
        FOREIGN KEY (normalization_run_id, source_observation_id)
        REFERENCES normalization_run_observations(normalization_run_id, source_observation_id)
        ON DELETE RESTRICT
);
CREATE INDEX idx_fact_source_observations_observation
    ON fact_source_observations (source_observation_id);
CREATE INDEX idx_fact_source_observations_run ON fact_source_observations (normalization_run_id);

CREATE TABLE market_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    security_id UUID NOT NULL REFERENCES securities(id) ON DELETE RESTRICT,
    metric_definition_id UUID NOT NULL REFERENCES metric_definitions(id) ON DELETE RESTRICT,
    normalization_run_id UUID NOT NULL
        REFERENCES normalization_runs(id) ON DELETE RESTRICT,
    series_key TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    supersedes_market_data_id UUID,
    value NUMERIC NOT NULL,
    unit_code TEXT NOT NULL,
    currency CHAR(3),
    as_of TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT market_data_series_nonempty CHECK (length(btrim(series_key)) > 0),
    CONSTRAINT market_data_version_positive CHECK (version_number > 0),
    CONSTRAINT market_data_unit_nonempty CHECK (length(btrim(unit_code)) > 0),
    CONSTRAINT market_data_id_company_unique UNIQUE (id, company_id),
    CONSTRAINT market_data_id_company_run_unique UNIQUE (id, company_id, normalization_run_id),
    CONSTRAINT market_data_version_unique
        UNIQUE (security_id, metric_definition_id, series_key, version_number),
    CONSTRAINT market_data_supersedes_fk
        FOREIGN KEY (supersedes_market_data_id, company_id)
        REFERENCES market_data(id, company_id) ON DELETE RESTRICT,
    CONSTRAINT market_data_not_self_superseding
        CHECK (supersedes_market_data_id IS NULL OR supersedes_market_data_id <> id),
    CONSTRAINT market_data_security_company_fk
        FOREIGN KEY (security_id, company_id)
        REFERENCES securities(id, company_id) ON DELETE RESTRICT
);
CREATE INDEX idx_market_data_security_metric_asof
    ON market_data (security_id, metric_definition_id, as_of DESC);
CREATE INDEX idx_market_data_company_metric_asof
    ON market_data (company_id, metric_definition_id, as_of DESC);
CREATE INDEX idx_market_data_normalization_run ON market_data (normalization_run_id);
CREATE INDEX idx_market_data_metric ON market_data (metric_definition_id);
CREATE INDEX idx_market_data_supersedes ON market_data (supersedes_market_data_id);

CREATE TABLE market_data_source_observations (
    market_data_id UUID NOT NULL,
    source_observation_id UUID NOT NULL,
    normalization_run_id UUID NOT NULL,
    company_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market_data_id, source_observation_id),
    CONSTRAINT market_data_source_market_fk
        FOREIGN KEY (market_data_id, company_id, normalization_run_id)
        REFERENCES market_data(id, company_id, normalization_run_id) ON DELETE RESTRICT,
    CONSTRAINT market_data_source_observation_fk
        FOREIGN KEY (source_observation_id, company_id)
        REFERENCES source_observations(id, company_id) ON DELETE RESTRICT,
    CONSTRAINT market_data_source_run_input_fk
        FOREIGN KEY (normalization_run_id, source_observation_id)
        REFERENCES normalization_run_observations(normalization_run_id, source_observation_id)
        ON DELETE RESTRICT
);
CREATE INDEX idx_market_data_source_observations_observation
    ON market_data_source_observations (source_observation_id);

CREATE TABLE valuation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    model_type TEXT NOT NULL,
    model_version TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    run_status TEXT NOT NULL DEFAULT 'RUNNING',
    inputs_hash TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    failure_message TEXT,
    created_by_user_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT valuation_runs_model_nonempty CHECK (length(btrim(model_type)) > 0),
    CONSTRAINT valuation_runs_version_nonempty CHECK (length(btrim(model_version)) > 0),
    CONSTRAINT valuation_runs_scenario_nonempty CHECK (length(btrim(scenario_name)) > 0),
    CONSTRAINT valuation_runs_status_valid
        CHECK (run_status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    CONSTRAINT valuation_runs_completion_valid
        CHECK ((run_status = 'RUNNING' AND completed_at IS NULL)
            OR (run_status IN ('COMPLETED', 'FAILED') AND completed_at IS NOT NULL)),
    CONSTRAINT valuation_runs_hash_sha256
        CHECK (inputs_hash IS NULL OR inputs_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT valuation_runs_id_company_unique UNIQUE (id, company_id)
);
CREATE INDEX idx_valuation_runs_company_started
    ON valuation_runs (company_id, started_at DESC);
CREATE INDEX idx_valuation_runs_status_started
    ON valuation_runs (run_status, started_at DESC);
CREATE INDEX idx_valuation_runs_model_type ON valuation_runs (model_type);

CREATE TABLE user_assumptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    assumption_key TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    value NUMERIC NOT NULL,
    unit_code TEXT NOT NULL,
    currency CHAR(3),
    notes TEXT,
    created_by_user_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_assumptions_key_nonempty CHECK (length(btrim(assumption_key)) > 0),
    CONSTRAINT user_assumptions_version_positive CHECK (version_number > 0),
    CONSTRAINT user_assumptions_unit_nonempty CHECK (length(btrim(unit_code)) > 0),
    CONSTRAINT user_assumptions_version_unique
        UNIQUE (company_id, assumption_key, version_number),
    CONSTRAINT user_assumptions_id_company_unique UNIQUE (id, company_id)
);
CREATE INDEX idx_user_assumptions_company_key
    ON user_assumptions (company_id, assumption_key, version_number DESC);

CREATE TABLE model_assumptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    valuation_run_id UUID NOT NULL,
    company_id UUID NOT NULL,
    assumption_key TEXT NOT NULL,
    value NUMERIC NOT NULL,
    unit_code TEXT NOT NULL,
    currency CHAR(3),
    source_user_assumption_id UUID,
    source_financial_fact_id UUID,
    source_description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT model_assumptions_key_nonempty CHECK (length(btrim(assumption_key)) > 0),
    CONSTRAINT model_assumptions_unit_nonempty CHECK (length(btrim(unit_code)) > 0),
    CONSTRAINT model_assumptions_one_source
        CHECK (source_user_assumption_id IS NULL OR source_financial_fact_id IS NULL),
    CONSTRAINT model_assumptions_run_key_unique UNIQUE (valuation_run_id, assumption_key),
    CONSTRAINT model_assumptions_run_company_fk
        FOREIGN KEY (valuation_run_id, company_id)
        REFERENCES valuation_runs(id, company_id) ON DELETE RESTRICT,
    CONSTRAINT model_assumptions_user_company_fk
        FOREIGN KEY (source_user_assumption_id, company_id)
        REFERENCES user_assumptions(id, company_id) ON DELETE RESTRICT,
    CONSTRAINT model_assumptions_fact_company_fk
        FOREIGN KEY (source_financial_fact_id, company_id)
        REFERENCES financial_facts(id, company_id) ON DELETE RESTRICT
);
CREATE INDEX idx_model_assumptions_source_user
    ON model_assumptions (source_user_assumption_id, company_id);
CREATE INDEX idx_model_assumptions_source_fact
    ON model_assumptions (source_financial_fact_id, company_id);

CREATE TABLE valuation_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    valuation_run_id UUID NOT NULL REFERENCES valuation_runs(id) ON DELETE RESTRICT,
    metric_definition_id UUID REFERENCES metric_definitions(id) ON DELETE RESTRICT,
    output_key TEXT NOT NULL,
    value NUMERIC NOT NULL,
    unit_code TEXT NOT NULL,
    currency CHAR(3),
    display_label TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT valuation_outputs_key_nonempty CHECK (length(btrim(output_key)) > 0),
    CONSTRAINT valuation_outputs_unit_nonempty CHECK (length(btrim(unit_code)) > 0),
    CONSTRAINT valuation_outputs_run_key_unique UNIQUE (valuation_run_id, output_key)
);
CREATE INDEX idx_valuation_outputs_metric ON valuation_outputs (metric_definition_id);

CREATE TABLE precedent_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_key TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    target_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    acquirer_company_id UUID REFERENCES companies(id) ON DELETE RESTRICT,
    announcement_date DATE,
    completion_date DATE,
    transaction_type TEXT,
    transaction_value NUMERIC,
    enterprise_value NUMERIC,
    equity_value NUMERIC,
    currency CHAR(3),
    revenue NUMERIC,
    ebitda NUMERIC,
    ebit NUMERIC,
    premium NUMERIC,
    geography TEXT,
    sector TEXT,
    supersedes_transaction_id UUID REFERENCES precedent_transactions(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT precedent_transactions_key_nonempty
        CHECK (length(btrim(transaction_key)) > 0),
    CONSTRAINT precedent_transactions_version_positive CHECK (version_number > 0),
    CONSTRAINT precedent_transactions_version_unique
        UNIQUE (transaction_key, version_number),
    CONSTRAINT precedent_transactions_not_self_superseding
        CHECK (supersedes_transaction_id IS NULL OR supersedes_transaction_id <> id),
    CONSTRAINT precedent_transactions_dates_valid
        CHECK (completion_date IS NULL OR announcement_date IS NULL
               OR completion_date >= announcement_date),
    CONSTRAINT precedent_transactions_currency_format
        CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')
);
CREATE INDEX idx_precedent_transactions_target_announcement
    ON precedent_transactions (target_company_id, announcement_date DESC);
CREATE INDEX idx_precedent_transactions_acquirer
    ON precedent_transactions (acquirer_company_id);
CREATE INDEX idx_precedent_transactions_sector_geography
    ON precedent_transactions (sector, geography);
CREATE INDEX idx_precedent_transactions_supersedes
    ON precedent_transactions (supersedes_transaction_id);

CREATE TABLE precedent_transaction_source_observations (
    precedent_transaction_id UUID NOT NULL
        REFERENCES precedent_transactions(id) ON DELETE RESTRICT,
    source_observation_id UUID NOT NULL
        REFERENCES source_observations(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (precedent_transaction_id, source_observation_id)
);
CREATE INDEX idx_precedent_transaction_source_observations_observation
    ON precedent_transaction_source_observations (source_observation_id);

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    action_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_ref TEXT,
    event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT audit_log_entity_type_nonempty CHECK (length(btrim(entity_type)) > 0),
    CONSTRAINT audit_log_action_type_nonempty CHECK (length(btrim(action_type)) > 0),
    CONSTRAINT audit_log_actor_type_nonempty CHECK (length(btrim(actor_type)) > 0)
);
CREATE INDEX idx_audit_log_entity ON audit_log (entity_type, entity_id, created_at DESC);
CREATE INDEX idx_audit_log_created_at ON audit_log (created_at DESC);

CREATE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'companies', 'source_systems', 'company_identifiers', 'securities',
        'filings', 'source_observations', 'normalization_runs',
        'normalization_run_observations', 'metric_definitions',
        'source_metric_mappings', 'financial_facts', 'fact_source_observations',
        'market_data', 'market_data_source_observations', 'valuation_runs',
        'user_assumptions', 'model_assumptions', 'valuation_outputs',
        'precedent_transactions'
    ]
    LOOP
        EXECUTE format(
            'CREATE TRIGGER %I BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            'trg_' || table_name || '_updated_at',
            table_name
        );
    END LOOP;
END;
$$;

CREATE FUNCTION reject_immutable_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% rows are append-only', TG_TABLE_NAME;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_source_observations_immutable
BEFORE UPDATE OR DELETE ON source_observations
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE TRIGGER trg_financial_facts_immutable
BEFORE UPDATE OR DELETE ON financial_facts
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE TRIGGER trg_metric_definitions_immutable
BEFORE UPDATE OR DELETE ON metric_definitions
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE FUNCTION validate_metric_definition_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    previous_metric_key TEXT;
    previous_version INTEGER;
BEGIN
    IF NEW.definition_version = 1 THEN
        IF NEW.supersedes_metric_definition_id IS NOT NULL THEN
            RAISE EXCEPTION 'Initial metric definition cannot supersede another definition';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.supersedes_metric_definition_id IS NULL THEN
        RAISE EXCEPTION 'Metric definition revisions must identify the prior definition';
    END IF;
    SELECT metric_key, definition_version
      INTO previous_metric_key, previous_version
      FROM metric_definitions
     WHERE id = NEW.supersedes_metric_definition_id;
    IF previous_metric_key IS DISTINCT FROM NEW.metric_key
       OR previous_version IS DISTINCT FROM NEW.definition_version - 1 THEN
        RAISE EXCEPTION 'Metric definition must supersede the prior version of the same metric';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_metric_definitions_version_guard
BEFORE INSERT ON metric_definitions
FOR EACH ROW EXECUTE FUNCTION validate_metric_definition_version();

CREATE TRIGGER trg_market_data_immutable
BEFORE UPDATE OR DELETE ON market_data
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER trg_user_assumptions_immutable
BEFORE UPDATE OR DELETE ON user_assumptions
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER trg_precedent_transactions_immutable
BEFORE UPDATE OR DELETE ON precedent_transactions
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER trg_precedent_transaction_source_observations_immutable
BEFORE UPDATE OR DELETE ON precedent_transaction_source_observations
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER trg_fact_source_observations_immutable
BEFORE UPDATE OR DELETE ON fact_source_observations
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER trg_market_data_source_observations_immutable
BEFORE UPDATE OR DELETE ON market_data_source_observations
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE FUNCTION guard_fact_provenance_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    parent_run_status TEXT;
BEGIN
    SELECT normalization_runs.run_status
      INTO parent_run_status
      FROM normalization_runs
     WHERE normalization_runs.id = NEW.normalization_run_id
     FOR UPDATE;
    IF parent_run_status IS DISTINCT FROM 'RUNNING' THEN
        RAISE EXCEPTION 'Fact provenance must be attached while normalization is RUNNING';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_fact_source_observations_insert_guard
BEFORE INSERT ON fact_source_observations
FOR EACH ROW EXECUTE FUNCTION guard_fact_provenance_insert();
CREATE TRIGGER trg_market_data_source_observations_insert_guard
BEFORE INSERT ON market_data_source_observations
FOR EACH ROW EXECUTE FUNCTION guard_fact_provenance_insert();

CREATE FUNCTION validate_financial_fact_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    previous_series_key TEXT;
    previous_version INTEGER;
    previous_metric_definition_id UUID;
BEGIN
    IF NEW.version_number = 1 THEN
        IF NEW.supersedes_fact_id IS NOT NULL THEN
            RAISE EXCEPTION 'Initial financial fact version cannot supersede another fact';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.supersedes_fact_id IS NULL THEN
        RAISE EXCEPTION 'Financial fact versions after version 1 must identify the prior version';
    END IF;
    SELECT series_key, version_number, metric_definition_id
      INTO previous_series_key, previous_version, previous_metric_definition_id
      FROM financial_facts
     WHERE id = NEW.supersedes_fact_id
       AND company_id = NEW.company_id;
    IF previous_series_key IS DISTINCT FROM NEW.series_key
       OR previous_version IS DISTINCT FROM NEW.version_number - 1
       OR previous_metric_definition_id IS DISTINCT FROM NEW.metric_definition_id THEN
        RAISE EXCEPTION 'Financial fact must supersede the previous version of the same series';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_financial_facts_version_guard
BEFORE INSERT ON financial_facts
FOR EACH ROW EXECUTE FUNCTION validate_financial_fact_version();

CREATE FUNCTION validate_market_data_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    previous_series_key TEXT;
    previous_version INTEGER;
    previous_metric_definition_id UUID;
    previous_security_id UUID;
BEGIN
    IF NEW.version_number = 1 THEN
        IF NEW.supersedes_market_data_id IS NOT NULL THEN
            RAISE EXCEPTION 'Initial market data version cannot supersede another record';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.supersedes_market_data_id IS NULL THEN
        RAISE EXCEPTION 'Market data versions after version 1 must identify the prior version';
    END IF;
    SELECT series_key, version_number, metric_definition_id, security_id
      INTO previous_series_key, previous_version,
           previous_metric_definition_id, previous_security_id
      FROM market_data
     WHERE id = NEW.supersedes_market_data_id
       AND company_id = NEW.company_id;
    IF previous_series_key IS DISTINCT FROM NEW.series_key
       OR previous_version IS DISTINCT FROM NEW.version_number - 1
       OR previous_metric_definition_id IS DISTINCT FROM NEW.metric_definition_id
       OR previous_security_id IS DISTINCT FROM NEW.security_id THEN
        RAISE EXCEPTION 'Market data must supersede the previous version of the same series';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_market_data_version_guard
BEFORE INSERT ON market_data
FOR EACH ROW EXECUTE FUNCTION validate_market_data_version();

CREATE FUNCTION validate_transaction_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    previous_key TEXT;
    previous_version INTEGER;
BEGIN
    IF NEW.version_number = 1 THEN
        IF NEW.supersedes_transaction_id IS NOT NULL THEN
            RAISE EXCEPTION 'Initial transaction version cannot supersede another transaction';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.supersedes_transaction_id IS NULL THEN
        RAISE EXCEPTION 'Transaction versions after version 1 must identify the prior version';
    END IF;
    SELECT transaction_key, version_number
      INTO previous_key, previous_version
      FROM precedent_transactions
     WHERE id = NEW.supersedes_transaction_id;
    IF previous_key IS DISTINCT FROM NEW.transaction_key
       OR previous_version IS DISTINCT FROM NEW.version_number - 1 THEN
        RAISE EXCEPTION 'Transaction must supersede the previous version of the same transaction';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_precedent_transactions_version_guard
BEFORE INSERT ON precedent_transactions
FOR EACH ROW EXECUTE FUNCTION validate_transaction_version();

CREATE FUNCTION guard_normalization_run_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.run_status <> 'RUNNING' THEN
        RAISE EXCEPTION 'Completed normalization runs are immutable';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.normalizer_name IS DISTINCT FROM OLD.normalizer_name
       OR NEW.normalization_version IS DISTINCT FROM OLD.normalization_version
       OR NEW.code_revision IS DISTINCT FROM OLD.code_revision
       OR NEW.started_at IS DISTINCT FROM OLD.started_at
       OR NEW.configuration IS DISTINCT FROM OLD.configuration
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'Normalization run inputs are immutable';
    END IF;
    IF NEW.run_status NOT IN ('RUNNING', 'COMPLETED', 'FAILED') THEN
        RAISE EXCEPTION 'Invalid normalization run state transition';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_normalization_runs_update_guard
BEFORE UPDATE ON normalization_runs
FOR EACH ROW EXECUTE FUNCTION guard_normalization_run_update();
CREATE TRIGGER trg_normalization_runs_delete_guard
BEFORE DELETE ON normalization_runs
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE FUNCTION guard_normalization_run_observation_write()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    parent_status TEXT;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        RAISE EXCEPTION 'Normalization run observations are append-only';
    END IF;
    SELECT run_status
      INTO parent_status
      FROM normalization_runs
     WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.normalization_run_id
                     ELSE NEW.normalization_run_id END
     FOR UPDATE;
    IF parent_status IS DISTINCT FROM 'RUNNING' THEN
        RAISE EXCEPTION 'Observations may only be attached while a normalization run is RUNNING';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_normalization_run_observations_guard
BEFORE INSERT OR UPDATE OR DELETE ON normalization_run_observations
FOR EACH ROW EXECUTE FUNCTION guard_normalization_run_observation_write();

CREATE FUNCTION guard_valuation_run_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.run_status <> 'RUNNING' THEN
        RAISE EXCEPTION 'Completed valuation runs are immutable';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.company_id IS DISTINCT FROM OLD.company_id
       OR NEW.model_type IS DISTINCT FROM OLD.model_type
       OR NEW.model_version IS DISTINCT FROM OLD.model_version
       OR NEW.scenario_name IS DISTINCT FROM OLD.scenario_name
       OR NEW.inputs_hash IS DISTINCT FROM OLD.inputs_hash
       OR NEW.started_at IS DISTINCT FROM OLD.started_at
       OR NEW.created_by_user_ref IS DISTINCT FROM OLD.created_by_user_ref
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'Valuation run inputs are immutable';
    END IF;
    IF NEW.run_status NOT IN ('RUNNING', 'COMPLETED', 'FAILED') THEN
        RAISE EXCEPTION 'Invalid valuation run state transition';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_valuation_runs_update_guard
BEFORE UPDATE ON valuation_runs
FOR EACH ROW EXECUTE FUNCTION guard_valuation_run_update();
CREATE TRIGGER trg_valuation_runs_delete_guard
BEFORE DELETE ON valuation_runs
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE FUNCTION guard_valuation_child_write()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    parent_status TEXT;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.valuation_run_id IS DISTINCT FROM OLD.valuation_run_id THEN
        RAISE EXCEPTION 'A valuation child cannot be moved between runs';
    END IF;
    SELECT run_status
      INTO parent_status
      FROM valuation_runs
     WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.valuation_run_id
                     ELSE NEW.valuation_run_id END
     FOR UPDATE;
    IF parent_status IS DISTINCT FROM 'RUNNING' THEN
        RAISE EXCEPTION 'Assumptions and outputs may only change while a valuation run is RUNNING';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_model_assumptions_run_guard
BEFORE INSERT OR UPDATE OR DELETE ON model_assumptions
FOR EACH ROW EXECUTE FUNCTION guard_valuation_child_write();
CREATE TRIGGER trg_valuation_outputs_run_guard
BEFORE INSERT OR UPDATE OR DELETE ON valuation_outputs
FOR EACH ROW EXECUTE FUNCTION guard_valuation_child_write();

CREATE FUNCTION reject_audit_log_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
    RETURN NULL;
END;
$$;
CREATE TRIGGER trg_audit_log_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION reject_audit_log_change();

CREATE FUNCTION require_fact_source_observation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM fact_source_observations
         WHERE financial_fact_id = NEW.id
    ) THEN
        RAISE EXCEPTION 'Financial fact % requires at least one source observation', NEW.id;
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER trg_financial_facts_require_provenance
AFTER INSERT ON financial_facts
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_fact_source_observation();

CREATE FUNCTION require_completed_normalization_run()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    parent_status TEXT;
BEGIN
    SELECT run_status
      INTO parent_status
      FROM normalization_runs
     WHERE id = NEW.normalization_run_id;
    IF parent_status IS DISTINCT FROM 'COMPLETED' THEN
        RAISE EXCEPTION 'Financial facts require a completed normalization run';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER trg_financial_facts_require_completed_normalization
AFTER INSERT ON financial_facts
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_completed_normalization_run();

CREATE FUNCTION require_market_data_provenance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM market_data_source_observations
         WHERE market_data_id = NEW.id
    ) THEN
        RAISE EXCEPTION 'Market data % requires at least one source observation', NEW.id;
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM normalization_runs
         WHERE id = NEW.normalization_run_id
           AND run_status = 'COMPLETED'
    ) THEN
        RAISE EXCEPTION 'Market data requires a completed normalization run';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER trg_market_data_require_provenance
AFTER INSERT ON market_data
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_market_data_provenance();

COMMIT;
