import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import Counter
import openai
import os
from typing import Dict, List, Any
import time
import random

class RedditPersonaScraper:
    def __init__(self, groq_api_key: str):
        """Initialize the Reddit Persona Scraper with Groq API"""
        # Configure for Groq API
        self.client = openai.OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_api_key
        )
        self.session = requests.Session()
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
    
    def extract_username_from_url(self, profile_url: str) -> str:
        """Extract username from Reddit profile URL"""
        patterns = [
            r'reddit\.com/user/([^/\?]+)',
            r'reddit\.com/u/([^/\?]+)',
            r'old\.reddit\.com/user/([^/\?]+)',
            r'old\.reddit\.com/u/([^/\?]+)',
            r'www\.reddit\.com/user/([^/\?]+)',
            r'www\.reddit\.com/u/([^/\?]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, profile_url.lower())
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract username from URL: {profile_url}")
    
    def scrape_reddit_profile(self, username: str) -> Dict[str, Any]:
        """Scrape Reddit user profile data from public pages"""
        print(f"Scraping profile for user: {username}")
        
        posts = []
        comments = []
        user_info = {'username': username}
        
        # Try to get user overview page first
        try:
            overview_url = f"https://old.reddit.com/user/{username}"
            print(f"Accessing: {overview_url}")
            
            response = self.session.get(overview_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract posts and comments from overview page
                things = soup.find_all('div', class_='thing')
                
                for thing in things[:50]:  # Limit to first 50 items
                    try:
                        # Check if it's a post or comment
                        if 'link' in thing.get('class', []):
                            # It's a post
                            title_elem = thing.find('a', class_='title')
                            title = title_elem.get_text(strip=True) if title_elem else "No title"
                            
                            subreddit_elem = thing.find('a', class_='subreddit')
                            subreddit = subreddit_elem.get_text(strip=True).replace('r/', '') if subreddit_elem else "unknown"
                            
                            score_elem = thing.find('div', class_='score')
                            score = self.extract_number_from_text(score_elem.get_text(strip=True) if score_elem else "0")
                            
                            posts.append({
                                'type': 'post',
                                'title': title,
                                'content': '',
                                'subreddit': subreddit,
                                'score': score,
                                'created_utc': time.time(),
                                'id': f"scraped_{len(posts)}"
                            })
                            
                        elif 'comment' in thing.get('class', []):
                            # It's a comment
                            comment_elem = thing.find('div', class_='md')
                            if comment_elem:
                                content = comment_elem.get_text(strip=True)
                                if len(content) > 10:
                                    
                                    subreddit_elem = thing.find('a', class_='subreddit')
                                    subreddit = subreddit_elem.get_text(strip=True).replace('r/', '') if subreddit_elem else "unknown"
                                    
                                    score_elem = thing.find('span', class_='score')
                                    score = self.extract_number_from_text(score_elem.get_text(strip=True) if score_elem else "0")
                                    
                                    comments.append({
                                        'type': 'comment',
                                        'content': content,
                                        'subreddit': subreddit,
                                        'score': score,
                                        'created_utc': time.time(),
                                        'id': f"scraped_{len(comments)}"
                                    })
                    except Exception as e:
                        print(f"Error processing item: {e}")
                        continue
                        
            time.sleep(random.uniform(2, 4))  # Rate limiting
            
        except Exception as e:
            print(f"Error scraping profile: {e}")
        
        # If no data found, create sample data for testing
        if not posts and not comments:
            print("No data found, creating sample data for testing...")
            posts = [
                {
                    'type': 'post',
                    'title': 'Sample post about technology',
                    'content': 'This is a sample post content about technology trends.',
                    'subreddit': 'technology',
                    'score': 100,
                    'created_utc': time.time(),
                    'id': 'sample_1'
                }
            ]
            comments = [
                {
                    'type': 'comment',
                    'content': 'This is a sample comment about programming and development.',
                    'subreddit': 'programming',
                    'score': 50,
                    'created_utc': time.time(),
                    'id': 'sample_2'
                }
            ]
        
        return {
            'user_info': user_info,
            'posts': posts,
            'comments': comments,
            'total_posts': len(posts),
            'total_comments': len(comments),
            'scrape_timestamp': datetime.now().isoformat()
        }
    
    def extract_number_from_text(self, text: str) -> int:
        """Extract number from text (for scores, upvotes, etc.)"""
        try:
            # Remove common text and extract numbers
            cleaned = re.sub(r'[^\d\-\+k]', '', text.lower())
            if 'k' in cleaned:
                num = float(cleaned.replace('k', '')) * 1000
                return int(num)
            return int(cleaned) if cleaned else 0
        except:
            return 0
    
    def analyze_user_behavior(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user behavior from scraped data"""
        posts = scraped_data['posts']
        comments = scraped_data['comments']
        all_content = posts + comments
        
        if not all_content:
            return {'error': 'No content available for analysis'}
        
        # Subreddit activity analysis
        subreddit_activity = Counter()
        for item in all_content:
            subreddit_activity[item['subreddit']] += 1
        
        # Content analysis
        total_post_length = sum(len(post.get('content', '')) + len(post.get('title', '')) for post in posts)
        total_comment_length = sum(len(comment.get('content', '')) for comment in comments)
        
        avg_post_length = total_post_length / len(posts) if posts else 0
        avg_comment_length = total_comment_length / len(comments) if comments else 0
        
        return {
            'top_subreddits': dict(subreddit_activity.most_common(10)),
            'avg_post_length': avg_post_length,
            'avg_comment_length': avg_comment_length,
            'total_activity': len(all_content),
            'post_comment_ratio': len(posts) / len(comments) if comments else float('inf')
        }
    
    def generate_persona_with_ai(self, scraped_data: Dict[str, Any], behavior_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate persona using Groq AI analysis"""
        
        sample_posts = scraped_data['posts'][:5]
        sample_comments = scraped_data['comments'][:10]
        username = scraped_data['user_info']['username']
        
        prompt = f"""
        Analyze this Reddit user's data and create a detailed user persona in professional UX research format.

        USER: {username}
        POSTS: {scraped_data['total_posts']}
        COMMENTS: {scraped_data['total_comments']}
        TOP SUBREDDITS: {behavior_analysis.get('top_subreddits', {})}

        SAMPLE POSTS:
        {json.dumps([{'title': p['title'], 'content': p['content'][:200], 'subreddit': p['subreddit']} for p in sample_posts], indent=2)}

        SAMPLE COMMENTS:
        {json.dumps([{'content': c['content'][:150], 'subreddit': c['subreddit']} for c in sample_comments], indent=2)}

        Create a professional user persona in JSON format:
        {{
            "name": "Professional persona name",
            "age": "Age range",
            "location": "Estimated location",
            "occupation": "Likely occupation",
            "bio": "2-3 sentence biography",
            "personality": {{
                "traits": ["trait1", "trait2", "trait3"],
                "communication_style": "Communication description"
            }},
            "goals": {{
                "primary": "Main goal",
                "secondary": "Secondary goal",
                "long_term": "Long-term aspiration"
            }},
            "frustrations": {{
                "technology": "Tech frustration",
                "community": "Community frustration",
                "personal": "Personal frustration"
            }},
            "motivations": {{
                "intrinsic": "Internal motivation",
                "extrinsic": "External motivation"
            }},
            "brands": ["brand1", "brand2", "brand3"],
            "quote": "Representative quote from their content"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama3-70b-8192",  # Groq's model
                messages=[
                    {"role": "system", "content": "You are an expert UX researcher. Create professional user personas. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"AI analysis error: {e}")
            # Return fallback persona
            return {
                "name": f"Digital Explorer {username}",
                "age": "25-35",
                "location": "Unknown",
                "occupation": "Tech Professional",
                "bio": f"Active Reddit user {username} with diverse interests across multiple communities.",
                "personality": {
                    "traits": ["curious", "engaged", "analytical"],
                    "communication_style": "Direct and informative"
                },
                "goals": {
                    "primary": "Stay informed about interests",
                    "secondary": "Engage with communities",
                    "long_term": "Build knowledge and connections"
                },
                "frustrations": {
                    "technology": "Platform limitations",
                    "community": "Low quality discussions",
                    "personal": "Information overload"
                },
                "motivations": {
                    "intrinsic": "Learning and growth",
                    "extrinsic": "Community recognition"
                },
                "brands": ["Reddit", "Tech Companies", "Online Services"],
                "quote": "Engaging with online communities to learn and share knowledge."
            }
    
    def load_html_template(self) -> str:
        """Load HTML template from file"""
        try:
            with open('persona_template.html', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise Exception("HTML template file 'persona_template.html' not found")
    
    def generate_html_persona(self, persona_data: Dict[str, Any], scraped_data: Dict[str, Any]) -> str:
        """Generate HTML persona report using template"""
        
        template = self.load_html_template()
        
        # Generate traits HTML
        traits_html = ""
        for trait in persona_data.get('personality', {}).get('traits', []):
            traits_html += f'<span class="trait-tag">{trait}</span>'
        
        # Generate brands HTML
        brands_html = ""
        for brand in persona_data.get('brands', []):
            brands_html += f'<span class="brand-tag">{brand}</span>'
        
        
        
        # Replace placeholders in template
        html_content = template.format(
            username=scraped_data['user_info']['username'],
            name=persona_data.get('name', 'Unknown User'),
            age=persona_data.get('age', 'Unknown'),
            location=persona_data.get('location', 'Unknown'),
            occupation=persona_data.get('occupation', 'Unknown'),
            bio=persona_data.get('bio', 'No biography available'),
            traits=traits_html,
            communication_style=persona_data.get('personality', {}).get('communication_style', 'Unknown'),
            primary_goal=persona_data.get('goals', {}).get('primary', 'Unknown'),
            secondary_goal=persona_data.get('goals', {}).get('secondary', 'Unknown'),
            long_term_goal=persona_data.get('goals', {}).get('long_term', 'Unknown'),
            tech_frustration=persona_data.get('frustrations', {}).get('technology', 'Unknown'),
            community_frustration=persona_data.get('frustrations', {}).get('community', 'Unknown'),
            personal_frustration=persona_data.get('frustrations', {}).get('personal', 'Unknown'),
            intrinsic_motivation=persona_data.get('motivations', {}).get('intrinsic', 'Unknown'),
            extrinsic_motivation=persona_data.get('motivations', {}).get('extrinsic', 'Unknown'),
            brands=brands_html,
            quote=persona_data.get('quote', 'No representative quote available'),
            
            timestamp=datetime.now().strftime('%B %d, %Y at %I:%M %p')
        )
        
        return html_content
    
    def save_html_persona(self, html_content: str, username: str, output_dir: str = "output") -> str:
        """Save HTML persona to file"""
        os.makedirs(output_dir, exist_ok=True)
    
        # Copy CSS file to output directory
        import shutil
        try:
            shutil.copy('styles.css', f"{output_dir}/styles.css")
            print(" CSS file copied to output folder")
        except FileNotFoundError:
            print(" Warning: styles.css not found")
    
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/persona_{username}_{timestamp}.html"
    
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
        return filename


    
    def generate_persona(self, profile_url: str) -> str:
        """Main method to generate persona from Reddit profile URL"""
        try:
            # Extract username from URL
            username = self.extract_username_from_url(profile_url)
            print(f"Processing user: {username}")
            
            # Scrape user data
            scraped_data = self.scrape_reddit_profile(username)
            print(f"Found {scraped_data['total_posts']} posts and {scraped_data['total_comments']} comments")
            
            # Analyze behavior
            behavior_analysis = self.analyze_user_behavior(scraped_data)
            
            # Generate persona with AI
            print("Generating persona with Groq AI...")
            persona_data = self.generate_persona_with_ai(scraped_data, behavior_analysis)
            
            # Generate HTML
            html_content = self.generate_html_persona(persona_data, scraped_data)
            
            # Save to file
            output_file = self.save_html_persona(html_content, username)
            print(f"Persona saved to: {output_file}")
            
            return output_file
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

def main():
    # Add your Groq API key here
    GROQ_API_KEY = "ADD_YOUR_GORQ_API_KEY"
    
    # Get Reddit URL from user input
    print("Reddit User Persona Generator (Groq AI)")
    print("=" * 45)
    profile_url = input("Enter Reddit profile URL: ")
    
    if not profile_url.strip():
        print("Error: Please provide a valid Reddit URL")
        return
    
    # Initialize scraper
    scraper = RedditPersonaScraper(GROQ_API_KEY)
    
    print(f"\nProcessing: {profile_url}")
    print("Please wait...")
    
    # Generate persona
    output_file = scraper.generate_persona(profile_url)
    
    if output_file:
        print(f"\nPersona generation completed!")
        print(f"HTML file: {output_file}")
        print(f"Open the HTML file in your browser to view the persona")
    else:
        print("\nPersona generation failed!")

if __name__ == "__main__":
    main()
