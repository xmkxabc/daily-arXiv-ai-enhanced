// Web Worker for JSON parsing to avoid blocking the main thread
self.onmessage = function(e) {
    const { url, month } = e.data;
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(papers => {
            // Send progress updates during processing
            const batchSize = 1000;
            const batches = [];
            
            for (let i = 0; i < papers.length; i += batchSize) {
                batches.push(papers.slice(i, i + batchSize));
            }
            
            // Send papers in batches to avoid large data transfer
            batches.forEach((batch, index) => {
                self.postMessage({
                    type: 'batch',
                    month: month,
                    papers: batch,
                    progress: {
                        current: (index + 1) * batchSize,
                        total: papers.length,
                        percentage: Math.round(((index + 1) / batches.length) * 100)
                    }
                });
            });
            
            self.postMessage({
                type: 'complete',
                month: month,
                totalPapers: papers.length
            });
        })
        .catch(error => {
            self.postMessage({
                type: 'error',
                month: month,
                error: error.message
            });
        });
};
