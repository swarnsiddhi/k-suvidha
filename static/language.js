let currentLanguage = 'en'; // Default language is English

// Translate text using LibreTranslate API
async function translateText(text, targetLanguage) {
    if (targetLanguage === 'en') return text; // No translation needed for English

    const response = await fetch(`https://libretranslate.com/translate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            q: text,
            target: targetLanguage,
            source: 'en', // Assuming the source language is English
            format: 'text',
        }),
    });

    const data = await response.json();
    return data.translatedText;
}

// Language switch event listener
document.getElementById('languageSelect').addEventListener('change', (event) => {
    currentLanguage = event.target.value;
    displayCommodities(allData); // Refresh the displayed content in the selected language
});
