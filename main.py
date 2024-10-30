import requests
import pandas as pd
import os
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np

# Set your GitHub token here (please do not expose your token publicly)
GITHUB_TOKEN = "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"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def fetch_users(city="Mumbai", min_followers=50):
    """Fetch GitHub users based on location and minimum followers."""
    url = f"https://api.github.com/search/users?q=location:{city}+followers:>{min_followers}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json().get("items", [])
    except requests.RequestException as e:
        print(f"Error fetching users: {e}")
        return []

def fetch_repositories(username):
    """Fetch all repositories for a given GitHub user."""
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            repos_data = response.json()
            if not repos_data:
                break
            repos.extend(repos_data)
            page += 1
        except requests.RequestException as e:
            print(f"Error fetching repositories for {username}: {e}")
            break
    return repos

def clean_company_name(company):
    """Clean company name by stripping and formatting."""
    return company.strip().lstrip('@').upper() if company else ""

def prepare_data(users):
    """Prepare a list of user and repository data."""
    users_list = []
    repos_list = []

    for user in users:
        user_data = {
            "login": user["login"],
            "name": user.get("name", ""),
            "company": clean_company_name(user.get("company", "")),
            "location": user.get("location", ""),
            "email": user.get("email", ""),
            "hireable": user.get("hireable", False),
            "bio": user.get("bio", ""),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "created_at": user.get("created_at", "")
        }
        users_list.append(user_data)

        # Fetch repositories for the user
        repos = fetch_repositories(user["login"])
        for repo in repos:
            license_name = repo.get("license", {}).get("name", "") if repo.get("license") else ""

            repos_data = {
                "login": user["login"],
                "full_name": repo["full_name"],
                "created_at": repo["created_at"],
                "stargazers_count": repo.get("stargazers_count", 0),
                "watchers_count": repo.get("watchers_count", 0),
                "language": repo.get("language", ""),
                "has_projects": repo.get("has_projects", False),
                "has_wiki": repo.get("has_wiki", False),
                "license_name": license_name
            }
            repos_list.append(repos_data)

    return users_list, repos_list

def create_csv_files(users, repos):
    """Create CSV files from users and repositories data."""
    users_df = pd.DataFrame(users)
    repos_df = pd.DataFrame(repos)

    users_df.to_csv("users.csv", index=False)
    repos_df.to_csv("repositories.csv", index=False)

def analyze_data(users, repos):
    recent_users = []
    for user in users:
        created_at = user.get('created_at', '')
        if created_at:  # Check if created_at is not empty
            try:
                user_year = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").year
                if user_year > 2020:
                    recent_users.append(user)
            except ValueError:
                print(f"Invalid date format for user: {user.get('login', 'Unknown')}, created_at: {created_at}")
        else:
            print(f"Empty created_at for user: {user.get('login', 'Unknown')}")  # Debug information

    # 1. Top 5 users by followers
    top_users = sorted(users, key=lambda x: x['followers'], reverse=True)[:5]
    top_users_logins = ', '.join([user['login'] for user in top_users])

    # 2. Earliest registered users
    earliest_users = sorted(users, key=lambda x: x['created_at'])[:5]
    earliest_users_logins = ', '.join([user['login'] for user in earliest_users])

    # 3. Most popular licenses
    license_counts = pd.Series([repo['license_name'] for repo in repos if repo['license_name']]).value_counts().head(3)
    popular_licenses = ', '.join(license_counts.index)

    # 4. Majority company
    companies = pd.Series([user['company'] for user in users if user['company']]).value_counts()
    majority_company = companies.idxmax() if not companies.empty else "N/A"

    # 5. Most popular programming language
    languages = pd.Series([repo['language'] for repo in repos if repo['language']]).value_counts()
    popular_language = languages.idxmax() if not languages.empty else "N/A"

    # 6. Second most popular language for users who joined after 2020
    recent_users = [user for user in users if user.get('created_at') and datetime.strptime(user['created_at'], "%Y-%m-%dT%H:%M:%SZ").year > 2020]
    recent_repos = [repo for repo in repos if repo['login'] in [user['login'] for user in recent_users]]
    recent_languages = pd.Series([repo['language'] for repo in recent_repos if repo['language']]).value_counts()
    second_popular_language = recent_languages.index[1] if len(recent_languages) > 1 else ""

    # 7. Language with highest average stars
    repos_df = pd.DataFrame(repos)  # Ensure repos_df is created from repos
    avg_stars = repos_df.groupby('language')['stargazers_count'].mean().idxmax() if not repos_df.empty else "N/A"

    # 8. Top 5 users by leader strength
    for user in users:
        user['leader_strength'] = user['followers'] / (1 + user['following']) if user['following'] else user['followers']
    top_leader_strength_users = sorted(users, key=lambda x: x['leader_strength'], reverse=True)[:5]
    top_leader_strength_logins = ', '.join([user['login'] for user in top_leader_strength_users])

    # 9. Correlation between followers and public repositories
    correlation_followers_repos = np.corrcoef(
        [user['followers'] for user in users], 
        [user['public_repos'] for user in users]
    )[0, 1]

    # 10. Regression followers on repos
    model = LinearRegression()
    model.fit(
        np.array([user['public_repos'] for user in users]).reshape(-1, 1), 
        np.array([user['followers'] for user in users]).reshape(-1, 1)
    )
    followers_per_repo = model.coef_[0][0]

    # 11. Correlation between projects and wiki enabled
    project_wiki_df = repos_df[['has_projects', 'has_wiki']]
    correlation_projects_wiki = project_wiki_df.corr().iloc[0, 1]

    # 12. Average following for hireable vs not hireable
    hireable_users = [user for user in users if user['hireable']]
    not_hireable_users = [user for user in users if not user['hireable']]
    avg_following_hireable = np.mean([user['following'] for user in hireable_users]) if hireable_users else 0
    avg_following_not_hireable = np.mean([user['following'] for user in not_hireable_users]) if not_hireable_users else 0
    hireable_following_diff = avg_following_hireable - avg_following_not_hireable

    # 13. Correlation of bio length with followers
    bio_lengths = [len(user['bio'].split()) for user in users if user['bio']]
    followers_counts = [user['followers'] for user in users if user['bio']]
    if bio_lengths and followers_counts:
        model_bio = LinearRegression()
        model_bio.fit(np.array(bio_lengths).reshape(-1, 1), np.array(followers_counts).reshape(-1, 1))
        bio_followers_corr = model_bio.coef_[0][0]
    else:
        bio_followers_corr = "N/A"

    # Prepare results dictionary
    results = {
        "top_users": top_users_logins,
        "earliest_users": earliest_users_logins,
        "popular_licenses": popular_licenses,
        "majority_company": majority_company,
        "popular_language": popular_language,
        "second_popular_language": second_popular_language,
        "avg_stars_language": avg_stars,
        "top_leader_strength": top_leader_strength_logins,
        "correlation_followers_repos": correlation_followers_repos,
        "followers_per_repo": followers_per_repo,
        "correlation_projects_wiki": correlation_projects_wiki,
        "hireable_following_diff": hireable_following_diff,
        "bio_followers_corr": bio_followers_corr
    }

    return results

def main():
    # Fetch users
    users = fetch_users(city="Mumbai", min_followers=50)
    
    # Prepare data
    users_data, repos_data = prepare_data(users)

    # Create CSV files
    create_csv_files(users_data, repos_data)

    # Analyze data
    analysis_results = analyze_data(users_data, repos_data)
    
    # Display analysis results
    for key, value in analysis_results.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()