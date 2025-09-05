export function ask(q) {
    return fetch('/api/ask', {method:"POST", headers: { "Content-Type":"application/json"}, body: JSON.stringlify({ question:q }) })
    .then(r => r.json());
}