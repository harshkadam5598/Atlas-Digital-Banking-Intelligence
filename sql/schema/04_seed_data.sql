-- ============================================================
-- Atlas – Reference / Seed Data
-- ============================================================
-- Static lookup values populated once at schema creation.
-- ETL pipeline inserts real synthetic customer/transaction data.
-- These seed rows are prerequisites for FK constraints.
-- ============================================================

-- ─── dim_country seed ─────────────────────────────────────────────────────────
INSERT INTO warehouse.dim_country
    (country_code, country_name, region, sub_region, currency_code, currency_factor, gdp_per_capita_band)
VALUES
    -- Western Europe
    ('GB', 'United Kingdom',  'Western Europe', 'Northern Europe', 'GBP', 1.000000, 'High'),
    ('DE', 'Germany',          'Western Europe', 'Central Europe',  'EUR', 0.860000, 'High'),
    ('FR', 'France',           'Western Europe', 'Western Europe',  'EUR', 0.860000, 'High'),
    ('NL', 'Netherlands',      'Western Europe', 'Western Europe',  'EUR', 0.860000, 'High'),
    ('IE', 'Ireland',          'Western Europe', 'Northern Europe', 'EUR', 0.860000, 'High'),
    ('ES', 'Spain',            'Southern Europe', 'Southern Europe','EUR', 0.860000, 'High'),
    ('IT', 'Italy',            'Southern Europe', 'Southern Europe','EUR', 0.860000, 'High'),
    ('PT', 'Portugal',         'Southern Europe', 'Southern Europe','EUR', 0.860000, 'Upper-Middle'),
    -- Nordics
    ('SE', 'Sweden',           'Nordics', 'Northern Europe',        'SEK', 0.074000, 'High'),
    ('NO', 'Norway',           'Nordics', 'Northern Europe',        'NOK', 0.073000, 'High'),
    ('DK', 'Denmark',          'Nordics', 'Northern Europe',        'DKK', 0.115000, 'High'),
    ('FI', 'Finland',          'Nordics', 'Northern Europe',        'EUR', 0.860000, 'High'),
    -- Eastern Europe
    ('PL', 'Poland',           'Eastern Europe', 'Eastern Europe',  'PLN', 0.194000, 'Upper-Middle'),
    ('RO', 'Romania',          'Eastern Europe', 'Eastern Europe',  'RON', 0.172000, 'Upper-Middle'),
    ('CZ', 'Czech Republic',   'Eastern Europe', 'Central Europe',  'CZK', 0.036000, 'Upper-Middle'),
    ('HU', 'Hungary',          'Eastern Europe', 'Central Europe',  'HUF', 0.002100, 'Upper-Middle'),
    -- Americas
    ('US', 'United States',    'Americas', 'North America',         'USD', 0.790000, 'High'),
    ('CA', 'Canada',           'Americas', 'North America',         'CAD', 0.580000, 'High'),
    ('BR', 'Brazil',           'Americas', 'South America',         'BRL', 0.150000, 'Upper-Middle'),
    -- APAC
    ('AU', 'Australia',        'APAC', 'Oceania',                   'AUD', 0.510000, 'High'),
    ('SG', 'Singapore',        'APAC', 'South-East Asia',           'SGD', 0.580000, 'High'),
    ('JP', 'Japan',            'APAC', 'East Asia',                 'JPY', 0.005100, 'High')
ON CONFLICT (country_code) DO NOTHING;

-- ─── dim_channel seed ─────────────────────────────────────────────────────────
INSERT INTO warehouse.dim_channel
    (channel_code, channel_name, campaign_type, is_paid, avg_cac_gbp)
VALUES
    ('ORGANIC_SEARCH', 'Organic Search',    'organic',     FALSE,  8.50),
    ('REFERRAL',       'Referral Program',  'referral',    FALSE, 12.00),
    ('GOOGLE_ADS',     'Google Ads',        'paid_search',  TRUE, 28.00),
    ('SOCIAL_META',    'Meta (FB/IG) Ads',  'paid_social',  TRUE, 35.00),
    ('SOCIAL_TIKTOK',  'TikTok Ads',        'paid_social',  TRUE, 42.00),
    ('INFLUENCER',     'Influencer',        'influencer',   TRUE, 55.00),
    ('EMAIL',          'Email Campaign',    'email',        TRUE, 18.00),
    ('DIRECT',         'Direct / Unknown',  'organic',     FALSE,  5.00)
ON CONFLICT (channel_code) DO NOTHING;

-- ─── dim_product seed ─────────────────────────────────────────────────────────
INSERT INTO warehouse.dim_product
    (product_code, product_name, product_category, revenue_model, fee_rate, monthly_fee_gbp, launch_date, is_premium_only)
VALUES
    ('DEBIT_CARD',     'Standard Debit Card',          'card',         'interchange',      0.0120, NULL,  '2021-01-01', FALSE),
    ('PREMIUM_SUB',    'Premium Subscription',         'subscription', 'subscription',     NULL,   9.99,  '2021-01-01', FALSE),
    ('SAVINGS_BASIC',  'Easy Access Savings',          'savings',      'transaction_fee',  0.0000, NULL,  '2021-03-01', FALSE),
    ('SAVINGS_VAULT',  'Savings Vault',                'savings',      'transaction_fee',  0.0000, NULL,  '2021-06-01', FALSE),
    ('INVEST_BASIC',   'Investment Portfolio',         'investment',   'aum_fee',          0.0075, NULL,  '2021-06-01', FALSE),
    ('INVEST_PREMIUM', 'Premium Investment Portfolio', 'investment',   'aum_fee',          0.0050, NULL,  '2022-01-01', TRUE),
    ('FX_STANDARD',    'Currency Exchange',            'transfer',     'spread',           0.0050, NULL,  '2021-01-01', FALSE),
    ('TRANSFER_INT',   'International Transfer',       'transfer',     'transaction_fee',  0.0040, NULL,  '2021-01-01', FALSE),
    ('TRANSFER_FREE',  'Free Local Transfer',          'transfer',     'transaction_fee',  0.0000, NULL,  '2021-01-01', FALSE),
    ('CRYPTO',         'Crypto Exchange',              'investment',   'spread',           0.0150, NULL,  '2022-06-01', TRUE)
ON CONFLICT (product_code) DO NOTHING;
