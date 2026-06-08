const puppeteer = require('puppeteer');

(async () => {
    try {
        const browser = await puppeteer.launch();
        const page = await browser.newPage();
        await page.goto("http://localhost:3000/");
        await page.waitForSelector("div#root", {timeout: 5000});
        
        // Let's just wait a moment to see if the UI renders.
        await new Promise(res => setTimeout(res, 2000));
        
        const text = await page.evaluate(() => {
            const el = document.querySelector("div#root:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(2) > div:nth-of-type(2) > div:nth-of-type(2) > div:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(2) > button:nth-of-type(1)");
            return el ? { text: el.textContent, disabled: el.disabled, className: el.className } : "Not found";
        });
        
        console.log("SELECTOR RESULT:", text);
        await browser.close();
    } catch(err) {
        console.error(err);
    }
})();
