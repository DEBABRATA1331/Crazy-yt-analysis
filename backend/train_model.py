import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import urllib.request
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_curve, auc

def download_dataset():
    print("Downloading dataset...")
    url = "https://raw.githubusercontent.com/Ankit152/IMDB-sentiment-analysis/master/IMDB-Dataset.csv"
    if not os.path.exists("imdb_dataset.csv"):
        try:
            urllib.request.urlretrieve(url, "imdb_dataset.csv")
            print("Dataset downloaded successfully.")
        except Exception as e:
            print(f"Failed to download dataset: {e}")
            # Fallback to a mock dataset
            print("Creating a mock dataset for demonstration...")
            data = {
                'review': [
                    "This is an amazing video, I loved it!", "Terrible content, complete waste of time.",
                    "Great explanation, very helpful.", "I hated this, so boring.",
                    "Absolutely fantastic work!", "Worst video I have ever seen.",
                    "This channel is great.", "I dislike the presentation style.",
                    "Brilliant insights, thank you.", "This is awful and misleading."
                ] * 100, # 1000 rows
                'sentiment': ['positive', 'negative', 'positive', 'negative', 'positive', 'negative', 'positive', 'negative', 'positive', 'negative'] * 100
            }
            pd.DataFrame(data).to_csv("imdb_dataset.csv", index=False)
    else:
        print("Dataset already exists.")

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"<br />", " ", text) # remove html tags
    text = re.sub(r"[^\w\s]", "", text) # remove punctuation
    return text

def run_ml_pipeline():
    download_dataset()
    
    print("Loading data...")
    df = pd.read_csv("imdb_dataset.csv")
    
    # Use a subset of 10000 if larger for faster training in demonstration
    if len(df) > 10000:
        df = df.sample(10000, random_state=42)
        
    print(f"Dataset size: {len(df)} rows")
    
    print("Preprocessing data...")
    df['review'] = df['review'].apply(preprocess_text)
    # Map sentiment to binary
    df['sentiment'] = df['sentiment'].map({'positive': 1, 'negative': 0})
    
    # Drop NAs if any
    df = df.dropna()
    
    X = df['review']
    y = df['sentiment']
    
    print("Splitting dataset...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Vectorizing text (TF-IDF)...")
    vectorizer = TfidfVectorizer(max_features=5000)
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)
    
    print("Training Logistic Regression model...")
    model = LogisticRegression(random_state=42)
    model.fit(X_train_tfidf, y_train)
    
    print("Evaluating model...")
    y_pred = model.predict(X_test_tfidf)
    y_prob = model.predict_proba(X_test_tfidf)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {accuracy:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))
    
    # ---------------------------------------------------------
    # GENERATE GRAPHS
    # ---------------------------------------------------------
    print("Generating evaluation graphs...")
    os.makedirs("graphs", exist_ok=True)
    
    # 1. Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Negative', 'Positive'], yticklabels=['Negative', 'Positive'])
    plt.title('Confusion Matrix')
    plt.ylabel('Actual Label')
    plt.xlabel('Predicted Label')
    plt.savefig('graphs/confusion_matrix.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. ROC Curve
    fpr, tpr, thresholds = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.savefig('graphs/roc_curve.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("Graphs saved in 'graphs' directory.")
    
    # ---------------------------------------------------------
    # SAVE MODEL
    # ---------------------------------------------------------
    print("Saving model and vectorizer...")
    joblib.dump(model, 'sentiment_model.pkl')
    joblib.dump(vectorizer, 'vectorizer.pkl')
    print("Saved as 'sentiment_model.pkl' and 'vectorizer.pkl'.")

if __name__ == "__main__":
    run_ml_pipeline()
