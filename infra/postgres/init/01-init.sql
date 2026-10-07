CREATE TABLE IF NOT EXISTS mesures_capteurs (
    id BIGSERIAL PRIMARY KEY,
    temperature_c NUMERIC(5,2),
    humidite_pct NUMERIC(5,2),
    niveau_gaz NUMERIC(8,2),
    presence_detectee BOOLEAN,
    date_mesure TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alertes (
    id BIGSERIAL PRIMARY KEY,
    type_alerte VARCHAR(50) NOT NULL,
    gravite VARCHAR(20) NOT NULL,
    message TEXT,
    date_creation TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acquittee BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS statut_boitier (
    id BIGSERIAL PRIMARY KEY,
    nom_boitier VARCHAR(100) NOT NULL,
    statut VARCHAR(30) NOT NULL,
    wifi_connecte BOOLEAN NOT NULL DEFAULT FALSE,
    adresse_ip INET,
    date_mise_a_jour TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
