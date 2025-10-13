# GitHub Archive API Usage Guide

## Overview

**GH Archive** is an open-source project that records the public GitHub timeline, archives it, and makes it easily accessible for further analysis. It captures all public GitHub activities from millions of developers working on open-source projects worldwide.

## What Data is Available?

GitHub provides 15+ event types including:
- New commits and fork events
- Opening new tickets/issues
- Comments on issues and pull requests
- Adding members to a project
- And more...

These events are aggregated into **hourly archives** in JSON format.

## Data Access Methods

### 1. Direct HTTP Access

You can download raw archive data using any HTTP client. Archives are available in `.json.gz` format.

#### Query Examples

| Query | Command |
|-------|---------|
| Activity for a specific hour (1/1/2015 @ 3PM UTC) | `wget https://data.gharchive.org/2015-01-01-15.json.gz` |
| Activity for a full day (1/1/2015) | `wget https://data.gharchive.org/2015-01-01-{0..23}.json.gz` |
| Activity for a full month (January 2015) | `wget https://data.gharchive.org/2015-01-{01..31}-{0..23}.json.gz` |

#### URL Format

```
https://data.gharchive.org/{YYYY-MM-DD-H}.json.gz
```

Where:
- `YYYY` = 4-digit year
- `MM` = 2-digit month (01-12)
- `DD` = 2-digit day (01-31)
- `H` = Hour in UTC (0-23)

### 2. Processing Downloaded Data

Each archive contains JSON encoded events as reported by the GitHub API. Here's an example Ruby script to download and parse an archive:

```ruby
require 'open-uri'
require 'zlib'
require 'yajl'

gz = open('http://data.gharchive.org/2015-01-01-12.json.gz')
js = Zlib::GzipReader.new(gz).read

Yajl::Parser.parse(js) do |event|
  print event
end
```

## Data Availability Timeline

- **Starting from 2/12/2011**: Activity archives are available
- **2/12/2011 - 12/31/2014**: Recorded from the (now deprecated) Timeline API
- **From 1/1/2015 onwards**: Recorded from the Events API

## Analyzing Data with Google BigQuery

### Getting Started

The entire GH Archive is available as a public dataset on **Google BigQuery**, automatically updated every hour.

#### Setup Steps

1. **Create a Google Cloud Project** (if you don't have one)
   - Login to [Google Developer Console](https://console.cloud.google.com/)
   - Create a new project
   - Activate the BigQuery API

2. **Access BigQuery**
   - Go to [BigQuery](https://console.cloud.google.com/bigquery)
   - Select your project from the dropdown in the header bar

3. **Execute Queries**
   - Use the public dataset name: `githubarchive`

### BigQuery Dataset Structure

GH Archive provides three types of tables for flexible querying:

| Dataset Type | Description | Example |
|--------------|-------------|---------|
| **year** | All activities for a specific year | `githubarchive.year.2015` |
| **month** | All activities for a specific month | `githubarchive.month.201501` |
| **day** | All activities for a specific day | `githubarchive.day.20150101` |

### Query Examples

#### Example 1: Count Issues by Status

```sql
/* Count of issues opened, closed, and reopened on 2019/01/01 */
SELECT event as issue_status, COUNT(*) as cnt 
FROM (
  SELECT type, repo.name, actor.login,
    JSON_EXTRACT(payload, '$.action') as event, 
  FROM `githubarchive.day.20190101`
  WHERE type = 'IssuesEvent'
)
GROUP BY issue_status;
```

#### Example 2: Count Push Events in Date Range

```sql
/* Count number of pushes between Jan 1 and Jan 5 */
SELECT COUNT(*) 
FROM `githubarchive.day.2015*`
WHERE 
  type = 'PushEvent'
  AND (_TABLE_SUFFIX BETWEEN '0101' AND '0105')
```

#### Example 3: Count Watch Events by Month

```sql
/* Count number of watches between Jan~Oct 2014 */
SELECT COUNT(*) 
FROM `githubarchive.month.2014*`
WHERE 
  type = 'WatchEvent'
  AND (_TABLE_SUFFIX BETWEEN '01' AND '10')
```

#### Example 4: Count Fork Events by Year

```sql
/* Count number of forks in 2012~2014 */
SELECT COUNT(*) 
FROM `githubarchive.year.20*`
WHERE 
  type = 'ForkEvent'
  AND (_TABLE_SUFFIX BETWEEN '12' AND '14')
```

### Schema Information

The BigQuery tables contain:
- **Distinct columns** for common activity fields (e.g., type, repo, actor)
- **`payload` field**: JSON string containing event-specific data (varies by event type)
- **`other` field**: JSON string containing additional GitHub-provided data not in the predefined schema

### Important Notes

- **Free Tier**: You get **1 TB of data processed per month** free of charge
- **Optimization Tip**: Use table wildcards and filter by `_TABLE_SUFFIX` to scan only relevant time ranges
- **JSON Functions**: Use BigQuery JSON functions like `JSON_EXTRACT()` to parse the `payload` field

## Common Event Types

Here are some commonly used event types you can filter for:

- `PushEvent` - Code pushes
- `WatchEvent` - Repository stars
- `ForkEvent` - Repository forks
- `IssuesEvent` - Issue creation/updates
- `PullRequestEvent` - Pull request activity
- `CreateEvent` - Branch or tag creation
- `DeleteEvent` - Branch or tag deletion
- `CommitCommentEvent` - Comments on commits
- `IssueCommentEvent` - Comments on issues
- `PullRequestReviewCommentEvent` - Comments on pull request reviews

## Best Practices

1. **Start Small**: Test your queries on daily tables before scaling to monthly or yearly tables
2. **Use Filters**: Always filter by event type and date ranges to minimize data scanning
3. **Extract Carefully**: When working with the `payload` field, understand the structure for each event type
4. **Monitor Costs**: Keep track of your BigQuery usage to stay within free tier limits
5. **Cache Results**: Store intermediate results in your own tables for complex analyses

## Additional Resources

- **Official Website**: https://www.gharchive.org/
- **GitHub Repository**: https://github.com/igrigorik/gharchive.org
- **BigQuery Console**: https://console.cloud.google.com/bigquery
- **GitHub API Documentation**: https://docs.github.com/en/rest

## Use Cases

- Track open-source project activity trends
- Analyze developer contributions across repositories
- Study programming language popularity
- Research collaboration patterns
- Build recommendation systems
- Monitor security vulnerabilities and patches
- Generate project insights and analytics

## Example Python Script

```python
import gzip
import json
import urllib.request

# Download and parse a single hour of activity
url = 'https://data.gharchive.org/2015-01-01-12.json.gz'

with urllib.request.urlopen(url) as response:
    with gzip.GzipFile(fileobj=response) as gz:
        for line in gz:
            event = json.loads(line)
            print(f"Event type: {event['type']}, Repo: {event['repo']['name']}")
```

## Support and Community

For questions, issues, or contributions:
- Check the [GH Archive GitHub repository](https://github.com/igrigorik/gharchive.org)
- Review community projects and research using GH Archive data
- Submit pull requests for documentation improvements

---

*Last updated: October 2025*

