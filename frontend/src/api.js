export async function checkHealth() {
    const res = await fetch('/api/health');
    return res.json();
}

export async function searchDocuments(query, top_k = 5) {
    const res = await fetch ('/api/serach',{
        method: 'POST',
        headers: {'Content-Type' : 'application/json' },
        body: JSON.stringify({ query, top_k })
    })
}return res.json();
