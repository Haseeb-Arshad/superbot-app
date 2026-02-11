// background.js

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url && !tab.url.startsWith('chrome://')) {

        // Execute content script to get body text
        chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: () => document.body.innerText
        }, (results) => {
            if (results && results[0]) {
                const bodyText = results[0].result;
                sendToSuperBot(tab.url, tab.title, bodyText);
            }
        });
    }
});

function sendToSuperBot(url, title, content) {
    fetch('http://localhost:8000/ingest-browser', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: url,
            title: title,
            content: content
        })
    })
        .then(response => console.log("Sent to Super-Bot:", response.status))
        .catch(error => console.error("Error sending to Super-Bot:", error));
}
