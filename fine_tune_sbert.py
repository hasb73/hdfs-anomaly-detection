"""fine_tune_sbert.py
Script to fine-tune a Sentence-Transformers model using a contrastive objective (SimCSE-like)
on a dataset of log pairs. This expects datasets prepared as JSONL with fields:
  - text_a
  - text_b
  - label (1 if similar/normal pair, 0 if dissimilar/anomalous)
For HDFS you'd generate pairs based on temporal proximity (positive) and random negative sampling.

Note: This script requires `sentence-transformers` and `torch` and is intended to run on GPU for speed.
"""
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import json, argparse, os

def load_pairs(path, max_samples=None):
    examples = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if max_samples and i >= max_samples: break
            obj = json.loads(line)
            text_a = obj.get('text_a')
            text_b = obj.get('text_b')
            label = obj.get('label', 1)
            examples.append(InputExample(texts=[text_a, text_b], label=float(label)))
    return examples

def main(args):
    model = SentenceTransformer(args.model_name_or_path)
    train_examples = load_pairs(args.train_pairs, max_samples=args.max_samples)
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.ContrastiveLoss(model)
    model.fit(train_objectives=[(train_dataloader, train_loss)],
              epochs=args.epochs,
              output_path=args.output_dir)
    print('Saved model to', args.output_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--train_pairs', type=str, required=True)
    parser.add_argument('--model_name_or_path', type=str, default='sentence-transformers/all-MiniLM-L6-v2')
    parser.add_argument('--output_dir', type=str, default='sbert_finetuned')
    parser.add_argument('--epochs', type=int, default=1)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--max_samples', type=int, default=None)
    args = parser.parse_args()
    main(args)
