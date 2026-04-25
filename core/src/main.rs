use serde::{Deserialize, Serialize};
use std::io::{self, BufRead};

#[derive(Serialize, Deserialize, Debug)]
struct ComputeRequest {
    model: String,
    prompt: String,
    system: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        let line = line?;
        let req: ComputeRequest = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(_) => continue,
        };

        let client = reqwest::Client::new();
        let mut res = client
            .post("http://localhost:11434/api/generate")
            .json(&serde_json::json!({
                "model": req.model,
                "prompt": req.prompt,
                "system": req.system,
                "stream": true,
                "options": {
                    "temperature": 0.9,
                    "num_predict": 512
                },
                "keep_alive": -1
            }))
            .send()
            .await?;

        while let Some(chunk) = res.chunk().await? {
            tokio::io::copy(&mut chunk.as_ref(), &mut tokio::io::stdout()).await?;
        }
    }
    Ok(())
}
