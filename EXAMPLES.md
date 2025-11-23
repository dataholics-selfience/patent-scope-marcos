# Exemplos de Uso - Patent Scraper API

## Python

```python
import requests
import json

# URL da API (substitua pela sua URL do Railway)
API_URL = "http://localhost:8000"  # ou "https://seu-app.railway.app"

# 1. Buscar por molécula
def search_molecule(molecule, page=1, page_size=10):
    response = requests.post(
        f"{API_URL}/search",
        json={
            "molecule": molecule,
            "search_type": "exact",
            "page": page,
            "page_size": page_size
        }
    )
    return response.json()

# 2. Obter detalhes de patente
def get_patent(patent_id):
    response = requests.get(f"{API_URL}/patent/{patent_id}")
    return response.json()

# Exemplos de uso
if __name__ == "__main__":
    # Buscar glucose
    results = search_molecule("glucose", page=1, page_size=5)
    
    print(f"Total: {results['pagination']['total_results']} patentes")
    
    for patent in results['results']:
        print(f"\n{patent['publication_number']}: {patent['title']}")
        print(f"Aplicantes: {', '.join(patent['applicants'])}")
```

## JavaScript (Node.js)

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8000';

// 1. Buscar por molécula
async function searchMolecule(molecule, page = 1, pageSize = 10) {
    try {
        const response = await axios.post(`${API_URL}/search`, {
            molecule: molecule,
            search_type: 'exact',
            page: page,
            page_size: pageSize
        });
        return response.data;
    } catch (error) {
        console.error('Erro:', error.response?.data || error.message);
        throw error;
    }
}

// 2. Obter detalhes de patente
async function getPatent(patentId) {
    const response = await axios.get(`${API_URL}/patent/${patentId}`);
    return response.data;
}

// Exemplo de uso
(async () => {
    const results = await searchMolecule('aspirin', 1, 5);
    
    console.log(`Total: ${results.pagination.total_results} patentes`);
    
    results.results.forEach(patent => {
        console.log(`\n${patent.publication_number}: ${patent.title}`);
        console.log(`Aplicantes: ${patent.applicants.join(', ')}`);
    });
})();
```

## JavaScript (Browser/Fetch)

```javascript
const API_URL = 'https://seu-app.railway.app';

// Buscar por molécula
async function searchMolecule(molecule) {
    const response = await fetch(`${API_URL}/search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            molecule: molecule,
            search_type: 'exact',
            page: 1,
            page_size: 10
        })
    });
    
    const data = await response.json();
    return data;
}

// Usar na página
searchMolecule('caffeine').then(data => {
    console.log('Resultados:', data.results);
    
    // Renderizar na página
    const container = document.getElementById('results');
    data.results.forEach(patent => {
        const div = document.createElement('div');
        div.innerHTML = `
            <h3>${patent.publication_number}</h3>
            <p>${patent.title}</p>
            <a href="${patent.url}" target="_blank">Ver patente</a>
        `;
        container.appendChild(div);
    });
});
```

## cURL

```bash
# 1. Health check
curl "http://localhost:8000/health"

# 2. Buscar por fórmula molecular
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "C6H12O6",
    "search_type": "exact",
    "page": 1,
    "page_size": 10
  }'

# 3. Buscar por nome
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "aspirin",
    "page": 1,
    "page_size": 20
  }'

# 4. Buscar com paginação
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "glucose",
    "page": 2,
    "page_size": 10
  }'

# 5. Obter detalhes de patente
curl "http://localhost:8000/patent/WO2023123456"
```

## PHP

```php
<?php

$API_URL = 'http://localhost:8000';

// 1. Buscar por molécula
function searchMolecule($molecule, $page = 1, $pageSize = 10) {
    global $API_URL;
    
    $data = [
        'molecule' => $molecule,
        'search_type' => 'exact',
        'page' => $page,
        'page_size' => $pageSize
    ];
    
    $options = [
        'http' => [
            'header'  => "Content-Type: application/json\r\n",
            'method'  => 'POST',
            'content' => json_encode($data)
        ]
    ];
    
    $context  = stream_context_create($options);
    $result = file_get_contents("$API_URL/search", false, $context);
    
    return json_decode($result, true);
}

// 2. Obter detalhes de patente
function getPatent($patentId) {
    global $API_URL;
    $result = file_get_contents("$API_URL/patent/$patentId");
    return json_decode($result, true);
}

// Exemplo de uso
$results = searchMolecule('penicillin', 1, 5);

echo "Total: " . $results['pagination']['total_results'] . " patentes\n\n";

foreach ($results['results'] as $patent) {
    echo $patent['publication_number'] . ": " . $patent['title'] . "\n";
    echo "Aplicantes: " . implode(', ', $patent['applicants']) . "\n\n";
}
?>
```

## Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
)

const API_URL = "http://localhost:8000"

type SearchRequest struct {
    Molecule   string `json:"molecule"`
    SearchType string `json:"search_type"`
    Page       int    `json:"page"`
    PageSize   int    `json:"page_size"`
}

type Patent struct {
    PatentID          string   `json:"patent_id"`
    PublicationNumber string   `json:"publication_number"`
    Title             string   `json:"title"`
    Abstract          string   `json:"abstract"`
    Applicants        []string `json:"applicants"`
    URL               string   `json:"url"`
}

type SearchResponse struct {
    Status  string    `json:"status"`
    Query   string    `json:"query"`
    Results []Patent  `json:"results"`
}

func searchMolecule(molecule string, page int, pageSize int) (*SearchResponse, error) {
    reqBody := SearchRequest{
        Molecule:   molecule,
        SearchType: "exact",
        Page:       page,
        PageSize:   pageSize,
    }
    
    jsonData, err := json.Marshal(reqBody)
    if err != nil {
        return nil, err
    }
    
    resp, err := http.Post(
        fmt.Sprintf("%s/search", API_URL),
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    body, err := ioutil.ReadAll(resp.Body)
    if err != nil {
        return nil, err
    }
    
    var result SearchResponse
    err = json.Unmarshal(body, &result)
    if err != nil {
        return nil, err
    }
    
    return &result, nil
}

func main() {
    results, err := searchMolecule("caffeine", 1, 5)
    if err != nil {
        fmt.Println("Erro:", err)
        return
    }
    
    fmt.Printf("Query: %s\n", results.Query)
    fmt.Printf("Total de patentes encontradas\n\n")
    
    for _, patent := range results.Results {
        fmt.Printf("%s: %s\n", patent.PublicationNumber, patent.Title)
        fmt.Printf("URL: %s\n\n", patent.URL)
    }
}
```

## Ruby

```ruby
require 'net/http'
require 'json'
require 'uri'

API_URL = 'http://localhost:8000'

# Buscar por molécula
def search_molecule(molecule, page = 1, page_size = 10)
  uri = URI("#{API_URL}/search")
  
  http = Net::HTTP.new(uri.host, uri.port)
  request = Net::HTTP::Post.new(uri.path, {'Content-Type' => 'application/json'})
  
  request.body = {
    molecule: molecule,
    search_type: 'exact',
    page: page,
    page_size: page_size
  }.to_json
  
  response = http.request(request)
  JSON.parse(response.body)
end

# Exemplo de uso
results = search_molecule('glucose', 1, 5)

puts "Total: #{results['pagination']['total_results']} patentes"
puts

results['results'].each do |patent|
  puts "#{patent['publication_number']}: #{patent['title']}"
  puts "Aplicantes: #{patent['applicants'].join(', ')}"
  puts
end
```

## Postman Collection

```json
{
  "info": {
    "name": "Patent Scraper API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    },
    {
      "name": "Search by Molecule",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"molecule\": \"glucose\",\n  \"search_type\": \"exact\",\n  \"page\": 1,\n  \"page_size\": 10\n}"
        },
        "url": {
          "raw": "{{base_url}}/search",
          "host": ["{{base_url}}"],
          "path": ["search"]
        }
      }
    },
    {
      "name": "Get Patent Details",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/patent/:patent_id",
          "host": ["{{base_url}}"],
          "path": ["patent", ":patent_id"],
          "variable": [
            {
              "key": "patent_id",
              "value": "WO2023123456"
            }
          ]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    }
  ]
}
```
