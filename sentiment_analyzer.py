import string
from nltk.tokenize import word_tokenize
import matplotlib.pyplot as plt
from collections import Counter
from nltk.corpus import stopwords
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import os

# Download required NLTK data
try:
    nltk.download("punkt_tab", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("vader_lexicon", quiet=True)
except:
    pass

class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        # Create emotions.txt file if it doesn't exist
        self.create_emotions_file()
    
    def create_emotions_file(self):
        """Create emotions.txt file with sample emotion mappings"""
        emotions_data = """happy: joy
sad: sadness
angry: anger
excited: joy
disappointed: sadness
frustrated: anger
love: joy
hate: anger
wonderful: joy
terrible: sadness
amazing: joy
awful: sadness
great: joy
bad: sadness
good: joy
excellent: joy
poor: sadness
fantastic: joy
horrible: sadness
brilliant: joy
stupid: anger
smart: joy
dumb: anger
beautiful: joy
ugly: sadness
nice: joy
mean: anger
kind: joy
cruel: anger
funny: joy
boring: sadness
interesting: joy
annoying: anger
cool: joy
lame: sadness
awesome: joy
worst: sadness
best: joy
perfect: joy
disaster: sadness
success: joy
failure: sadness
win: joy
lose: sadness
victory: joy
defeat: sadness
celebrate: joy
mourn: sadness
laugh: joy
cry: sadness
smile: joy
frown: sadness
thrilled: joy
devastated: sadness
furious: anger
delighted: joy
miserable: sadness
ecstatic: joy
depressed: sadness
livid: anger
cheerful: joy
gloomy: sadness
outraged: anger
pleased: joy
upset: sadness
elated: joy
heartbroken: sadness
enraged: anger
content: joy
disappointed: sadness
overjoyed: joy
sorrowful: sadness
irate: anger
satisfied: joy
melancholy: sadness
blissful: joy
dejected: sadness
incensed: anger
optimistic: joy
pessimistic: sadness
euphoric: joy
despondent: sadness
indignant: anger
hopeful: joy
hopeless: sadness
jubilant: joy
forlorn: sadness
wrathful: anger
gleeful: joy
woeful: sadness
"""
        try:
            if not os.path.exists("emotions.txt"):
                with open("emotions.txt", "w") as file:
                    file.write(emotions_data.strip())
                print("Created emotions.txt file with emotion mappings")
        except Exception as e:
            print(f"Error creating emotions file: {e}")
    
    def analyze_emotions(self, text):
        """Analyze emotions in text"""
        try:
            # Convert to lowercase
            lower_case = text.lower()
            
            # Remove punctuation
            remove_text = lower_case.translate(str.maketrans("", "", string.punctuation))
            
            # Tokenize
            split_words = word_tokenize(remove_text, "english")
            
            # Remove stopwords
            final_words = []
            for word in split_words:
                if word not in stopwords.words("english"):
                    final_words.append(word)
            
            # Find emotions
            emotion_list = []
            try:
                with open("emotions.txt", "r") as file:
                    for line in file:
                        clear_line = line.replace("\n", "").replace(",", "").replace("'", "").strip()
                        if ":" in clear_line:
                            word, emotion = clear_line.split(":", 1)
                            if word.strip() in final_words:
                                emotion_list.append(emotion.strip())
            except FileNotFoundError:
                print("emotions.txt file not found")
                pass
            
            # Count emotions
            emotion_counts = Counter(emotion_list)
            return emotion_counts
            
        except Exception as e:
            print(f"Error analyzing emotions: {e}")
            return Counter()
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text"""
        try:
            # Remove punctuation for analysis
            clean_text = text.translate(str.maketrans("", "", string.punctuation))
            
            # Get sentiment scores
            scores = self.analyzer.polarity_scores(clean_text)
            negative = scores["neg"]
            positive = scores["pos"]
            neutral = scores["neu"]
            compound = scores["compound"]
            
            # Determine overall sentiment
            if compound >= 0.05:
                sentiment = "positive"
            elif compound <= -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return {
                "sentiment": sentiment,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "compound": compound
            }
            
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "positive": 0.0,
                "negative": 0.0,
                "neutral": 1.0,
                "compound": 0.0
            }
    
    def get_sentiment_color(self, sentiment):
        """Get color for sentiment (RGB values 0-1)"""
        if sentiment == "positive":
            return (0, 0.8, 0, 1)  # Green
        elif sentiment == "negative":
            return (1, 0, 0, 1)    # Red
        else:
            return (0.5, 0.5, 0.5, 1)  # Gray
    
    def create_emotion_graph(self, emotion_counts, save_path="emotions_graph.png"):
        """Create and save emotion analysis graph"""
        try:
            if not emotion_counts:
                print("No emotions to plot")
                return False
            
            # Create the graph
            fig, ax = plt.subplots(figsize=(10, 6))
            emotions = list(emotion_counts.keys())
            counts = list(emotion_counts.values())
            
            # Create bar chart
            bars = ax.bar(emotions, counts, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'])
            
            # Customize the graph
            ax.set_title('Emotion Analysis', fontsize=16, fontweight='bold')
            ax.set_xlabel('Emotions', fontsize=12)
            ax.set_ylabel('Frequency', fontsize=12)
            
            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom')
            
            # Adjust layout to prevent label cutoff
            plt.tight_layout()
            
            # Save the graph
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()  # Close to free memory
            
            print(f"Emotion graph saved as {save_path}")
            return True
            
        except Exception as e:
            print(f"Error creating emotion graph: {e}")
            return False
    
    def analyze_text_comprehensive(self, text):
        """Comprehensive analysis of text including sentiment and emotions"""
        try:
            # Get sentiment analysis
            sentiment_info = self.analyze_sentiment(text)
            
            # Get emotion analysis
            emotion_counts = self.analyze_emotions(text)
            
            # Create comprehensive report
            report = {
                "text": text,
                "sentiment": sentiment_info,
                "emotions": dict(emotion_counts),
                "summary": self.create_analysis_summary(sentiment_info, emotion_counts)
            }
            
            return report
            
        except Exception as e:
            print(f"Error in comprehensive analysis: {e}")
            return None
    
    def create_analysis_summary(self, sentiment_info, emotion_counts):
        """Create a human-readable summary of the analysis"""
        try:
            sentiment = sentiment_info['sentiment']
            
            summary = f"Overall sentiment: {sentiment.title()}"
            
            if emotion_counts:
                top_emotion = emotion_counts.most_common(1)[0][0]
                summary += f" | Primary emotion: {top_emotion.title()}"
                
                if len(emotion_counts) > 1:
                    summary += f" | {len(emotion_counts)} emotions detected"
            else:
                summary += " | No specific emotions detected"
            
            return summary
            
        except Exception as e:
            print(f"Error creating summary: {e}")
            return "Analysis unavailable"
    
    def batch_analyze(self, text_list):
        """Analyze multiple texts at once"""
        try:
            results = []
            for i, text in enumerate(text_list):
                print(f"Analyzing text {i+1}/{len(text_list)}: {text[:50]}...")
                analysis = self.analyze_text_comprehensive(text)
                if analysis:
                    results.append(analysis)
            
            return results
            
        except Exception as e:
            print(f"Error in batch analysis: {e}")
            return []

# Example usage and testing
if __name__ == "__main__":
    # Initialize the analyzer
    analyzer = SentimentAnalyzer()
    
    # Test messages
    test_messages = [
        "I'm so happy today! This is amazing!",
        "I hate this terrible situation. It's awful.",
        "The weather is okay, nothing special.",
        "I love spending time with my friends. They make me feel wonderful!",
        "This is the worst day ever. I'm so frustrated and angry."
    ]
    
    print("=== Sentiment Analysis Testing ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"Test {i}: {message}")
        
        # Analyze sentiment
        sentiment_result = analyzer.analyze_sentiment(message)
        print(f"Sentiment: {sentiment_result['sentiment'].title()}")
        print(f"Scores - Positive: {sentiment_result['positive']:.2f}, "
              f"Negative: {sentiment_result['negative']:.2f}, "
              f"Neutral: {sentiment_result['neutral']:.2f}")
        
        # Analyze emotions
        emotions = analyzer.analyze_emotions(message)
        if emotions:
            print("Emotions detected:")
            for emotion, count in emotions.most_common():
                print(f"  {emotion.title()}: {count}")
        else:
            print("No emotions detected")
        
        print("-" * 50)
    
    # Test comprehensive analysis
    print("\n=== Comprehensive Analysis Test ===")
    test_text = "I'm absolutely thrilled about this fantastic opportunity! It's going to be amazing!"
    comprehensive_result = analyzer.analyze_text_comprehensive(test_text)
    
    if comprehensive_result:
        print(f"Text: {comprehensive_result['text']}")
        print(f"Summary: {comprehensive_result['summary']}")
        print(f"Full sentiment data: {comprehensive_result['sentiment']}")
        print(f"Emotions: {comprehensive_result['emotions']}")
