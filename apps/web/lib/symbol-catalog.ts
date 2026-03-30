export type SymbolAssetType = "stock" | "etf" | "crypto";

export type SymbolCatalogEntry = {
  symbol: string;
  company: string;
  assetType: SymbolAssetType;
  category: string;
};

export const symbolCatalog: SymbolCatalogEntry[] = [
  { symbol: "AAPL", company: "Apple", assetType: "stock", category: "Mega Cap Tech" },
  { symbol: "MSFT", company: "Microsoft", assetType: "stock", category: "Mega Cap Tech" },
  { symbol: "NVDA", company: "NVIDIA", assetType: "stock", category: "Semiconductors" },
  { symbol: "AMD", company: "Advanced Micro Devices", assetType: "stock", category: "Semiconductors" },
  { symbol: "AVGO", company: "Broadcom", assetType: "stock", category: "Semiconductors" },
  { symbol: "MU", company: "Micron Technology", assetType: "stock", category: "Semiconductors" },
  { symbol: "INTC", company: "Intel", assetType: "stock", category: "Semiconductors" },
  { symbol: "QCOM", company: "Qualcomm", assetType: "stock", category: "Semiconductors" },
  { symbol: "AMZN", company: "Amazon", assetType: "stock", category: "Consumer & Retail" },
  { symbol: "TSLA", company: "Tesla", assetType: "stock", category: "Consumer & EV" },
  { symbol: "META", company: "Meta Platforms", assetType: "stock", category: "Internet Platforms" },
  { symbol: "GOOGL", company: "Alphabet Class A", assetType: "stock", category: "Internet Platforms" },
  { symbol: "GOOG", company: "Alphabet Class C", assetType: "stock", category: "Internet Platforms" },
  { symbol: "NFLX", company: "Netflix", assetType: "stock", category: "Media & Streaming" },
  { symbol: "PLTR", company: "Palantir Technologies", assetType: "stock", category: "Software & AI" },
  { symbol: "CRM", company: "Salesforce", assetType: "stock", category: "Software & AI" },
  { symbol: "ADBE", company: "Adobe", assetType: "stock", category: "Software & AI" },
  { symbol: "ORCL", company: "Oracle", assetType: "stock", category: "Software & AI" },
  { symbol: "SNOW", company: "Snowflake", assetType: "stock", category: "Software & AI" },
  { symbol: "SHOP", company: "Shopify", assetType: "stock", category: "Software & AI" },
  { symbol: "UBER", company: "Uber Technologies", assetType: "stock", category: "Mobility & Delivery" },
  { symbol: "RBLX", company: "Roblox", assetType: "stock", category: "Growth & Momentum" },
  { symbol: "COIN", company: "Coinbase Global", assetType: "stock", category: "Crypto Equities" },
  { symbol: "HOOD", company: "Robinhood Markets", assetType: "stock", category: "Financials" },
  { symbol: "JPM", company: "JPMorgan Chase", assetType: "stock", category: "Financials" },
  { symbol: "BAC", company: "Bank of America", assetType: "stock", category: "Financials" },
  { symbol: "GS", company: "Goldman Sachs", assetType: "stock", category: "Financials" },
  { symbol: "WFC", company: "Wells Fargo", assetType: "stock", category: "Financials" },
  { symbol: "SMCI", company: "Super Micro Computer", assetType: "stock", category: "Hardware & Infrastructure" },
  { symbol: "SPY", company: "SPDR S&P 500 ETF Trust", assetType: "etf", category: "Index ETF" },
  { symbol: "QQQ", company: "Invesco QQQ Trust", assetType: "etf", category: "Index ETF" },
  { symbol: "IWM", company: "iShares Russell 2000 ETF", assetType: "etf", category: "Index ETF" },
  { symbol: "DIA", company: "SPDR Dow Jones Industrial Average ETF", assetType: "etf", category: "Index ETF" },
  { symbol: "XLF", company: "Financial Select Sector SPDR Fund", assetType: "etf", category: "Sector ETF" },
  { symbol: "XLK", company: "Technology Select Sector SPDR Fund", assetType: "etf", category: "Sector ETF" },
  { symbol: "XLE", company: "Energy Select Sector SPDR Fund", assetType: "etf", category: "Sector ETF" },
  { symbol: "XBI", company: "SPDR S&P Biotech ETF", assetType: "etf", category: "Sector ETF" },
  { symbol: "SOXL", company: "Direxion Daily Semiconductor Bull 3X Shares", assetType: "etf", category: "Leveraged ETF" },
  { symbol: "TQQQ", company: "ProShares UltraPro QQQ", assetType: "etf", category: "Leveraged ETF" },
  { symbol: "BITO", company: "ProShares Bitcoin Strategy ETF", assetType: "etf", category: "Crypto ETF" },
  { symbol: "IBIT", company: "iShares Bitcoin Trust ETF", assetType: "etf", category: "Crypto ETF" },
  { symbol: "ETHA", company: "iShares Ethereum Trust ETF", assetType: "etf", category: "Crypto ETF" },
  { symbol: "BTC", company: "Bitcoin", assetType: "crypto", category: "Crypto Assets" },
  { symbol: "ETH", company: "Ethereum", assetType: "crypto", category: "Crypto Assets" },
  { symbol: "SOL", company: "Solana", assetType: "crypto", category: "Crypto Assets" },
  { symbol: "XRP", company: "XRP", assetType: "crypto", category: "Crypto Assets" },
  { symbol: "DOGE", company: "Dogecoin", assetType: "crypto", category: "Crypto Assets" },
  { symbol: "ADA", company: "Cardano", assetType: "crypto", category: "Crypto Assets" },
  { symbol: "AVAX", company: "Avalanche", assetType: "crypto", category: "Crypto Assets" },
  { symbol: "LINK", company: "Chainlink", assetType: "crypto", category: "Crypto Assets" },
];

export function getSymbolMetadata(symbol: string): SymbolCatalogEntry | null {
  return symbolCatalog.find((item) => item.symbol === symbol.toUpperCase()) ?? null;
}
