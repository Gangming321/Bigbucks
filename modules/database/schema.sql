DROP TABLE IF EXISTS stock_data;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS portfolio;
DROP TABLE IF EXISTS stock_overview;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  balance  BIGINT NOT NULL,
  is_admin BOOLEAN NOT NULL
);

CREATE TABLE stock_data (
   stock_symbol      VARCHAR(5)    NOT NULL,  
   closing_date      DATE          NOT NULL,
   open_price        DECIMAL(16,6) NOT NULL,
   high_price        DECIMAL(16,6) NOT NULL,
   low_price         DECIMAL(16,6) NOT NULL,
   close_price       DECIMAL(16,6) NOT NULL,
   adj_close_price   DECIMAL(16,6) NOT NULL,
   volume            BIGINT        NOT NULL,
   PRIMARY KEY (stock_symbol, closing_date)
);

CREATE TABLE transactions (
   transaction_id    INTEGER PRIMARY KEY AUTOINCREMENT,
   transaction_date  DATE          NOT NULL,
   user_id           INTEGER       NOT NULL,
   transaction_type  char(5)       NOT NULL,
   symbol            VARCHAR(20)   NOT NULL,  
   unit_price        DECIMAL(16,6) NOT NULL,
   amount            BIGINT        NOT NULL
);

CREATE TABLE portfolio (
   record_id      INTEGER PRIMARY KEY AUTOINCREMENT,
   user_id           INTEGER        NOT NULL,
   stock_symbol      VARCHAR(5)     NOT NULL,
   quantity          BIGINT         NOT NULL, -- the position for specific stock
   average_cost      DECIMAL(16,6),
   FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE stock_overview(
   symbol            VARCHAR(5)     NOT NULL,
   company_name      VARCHAR(100)   NOT NULL,
   exchange          VARCHAR(20)    NOT NULL,  
   currency          VARCHAR(5)     NOT NULL,
   eps               DECIMAL(16,6)  NOT NULL,
   beta              DECIMAL(16,6)  NOT NULL,
   PRIMARY KEY (symbol)
);