const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const axios = require('axios');
const app = express();
const port = 3000;
const moment = require('moment-timezone')

app.use(cors());

let db = new sqlite3.Database('C:/Users/samue/2. Semester/Grundlagen Interaktiver Systeme/Projekt/finance.db', (err) => {
    if(err) {
        console.error(err.message);
    } else {
        console.log("Connected"); 
    }
});

async function getStockPrice(symbol) {
    try{
        if (!symbol) {
            console.error('Symbol is undefined');
            return null;
        }
        const end = moment.tz("US/Eastern");
        const start = end.clone().subtract(7, 'days');

        const url = `https://query1.finance.yahoo.com/v7/finance/download/${encodeURIComponent(symbol)}?period1=${Math.floor(start.unix())}&period2=${Math.floor(end.unix())}&interval=1d&events=history&includeAdjustedClose=true`;
        const response = await axios.get(url, {
            headers: {"User-Agent": "curl/7.68.0", "Accept": "*/*"}
        });
        
        const csv = response.data.split('\n');
        const quotes = csv.slice(1, -1).reverse();

        if (quotes.length > 0) {
            const lastLine = csv[csv.length - 2].split(',');
            const price = parseFloat(lastLine[5]);
            return price;
        } else {
            throw new Error('No data available for the given symbol');
        }
    } catch (error) {
        console.error('Error fetching data for ${symbol}: ', error);
        return null;
    }
}

app.get('/getStockPrice/:symbol', async (req, res) => {
    try {
        const symbol = req.params.symbol;
        db.get("SELECT price FROM stocks WHERE symbol = ?", [symbol], async (err, row) => {
            if (err) {
                console.error(err.message);
                return res.status(500).send("Database error");
            }
            const previousPrice = row ? row.price : 0;
            const currentPrice = await getStockPrice(symbol)

            if (currentPrice === null) {
                res.status(500).json({error: 'Error fetching stock price'});
                return;
            } 

            var tempPrice = previousPrice;
            let query = `UPDATE stocks SET price = ? WHERE symbol = ?`;
            db.run(query, [currentPrice, symbol], function(err) {
                if (err) {
                    return console.error(err.message);
                }

                res.json({symbol, currentPrice, tempPrice});
            });
        });
    } catch(error) {
        console.error(error.message);
        res.status(500).send("Server error")
    }
});

app.get('/grand-total', async (req, res) => {
    try {
        db.get("SELECT cash FROM users WHERE id = ?", [2], async (err, row) => {
            if (err) {
                console.error(err.message);
                return res.setMaxListeners(500).send("Database error");
            }
            const cashBalance = row.cash;
            
            db.all("SELECT symbol, shares FROM possesions WHERE user_id = ?", [2], async (err, rows) => {
                if (err) {
                    console.error(err.message);
                    return res.status(500).send("Database Error");
                }

                let totalStockValue = 0;
                for (const row of rows) {
                    const stockPrice = await getStockPrice(row.symbol);
                    if(stockPrice !== null) {
                        totalStockValue += stockPrice * row.shares;
                    }
                }
                const grandTotal = cashBalance + totalStockValue;
                res.json({ grandTotal });
            });
        });
    } catch (error) {
        console.error('Error: ', error);
        res.status(500).send("Server error");
    }
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});

