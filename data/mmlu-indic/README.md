---
language:
- bn
- en
- gu
- hi
- kn
- ml
- mr
- or
- pa
- ta
- te
license: mit
task_categories:
- question-answering
pretty_name: Indic MMLU
dataset_info:
- config_name: bn
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 9981094
  dataset_size: 14523284.181818182
- config_name: bn_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 5621536
    num_examples: 13894
  download_size: 3111687
  dataset_size: 5621536
- config_name: en
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 7046354
  dataset_size: 14523284.181818182
- config_name: gu
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 5048638
  dataset_size: 14523284.181818182
- config_name: gu_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 5948327
    num_examples: 14004
  download_size: 3281363
  dataset_size: 5948327
- config_name: hi
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 5060941
  dataset_size: 14523284.181818182
- config_name: hi_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 6192639
    num_examples: 13913
  download_size: 3308477
  dataset_size: 6192639
- config_name: kn
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 5391445
  dataset_size: 14523284.181818182
- config_name: kn_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 6507374
    num_examples: 14005
  download_size: 3391672
  dataset_size: 6507374
- config_name: ml
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 5422573
  dataset_size: 14523284.181818182
- config_name: ml_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 6666429
    num_examples: 13991
  download_size: 3527459
  dataset_size: 6666429
- config_name: mr
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 5205467
  dataset_size: 14523284.181818182
- config_name: mr_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 5949755
    num_examples: 13904
  download_size: 3339832
  dataset_size: 5949755
- config_name: or
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 4830686
  dataset_size: 14523284.181818182
- config_name: or_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 6088902
    num_examples: 13979
  download_size: 3235693
  dataset_size: 6088902
- config_name: pa
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 4959729
  dataset_size: 14523284.181818182
- config_name: pa_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 6072164
    num_examples: 13946
  download_size: 3375598
  dataset_size: 6072164
- config_name: ta
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 5621280
  dataset_size: 14523284.181818182
- config_name: ta_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 6178662
    num_examples: 13096
  download_size: 3264376
  dataset_size: 6178662
- config_name: te
  features:
  - name: question
    dtype: string
  - name: answer
    dtype: int64
  - name: choices
    sequence: string
  splits:
  - name: validation
    num_bytes: 239800.54545454544
    num_examples: 285
  - name: test
    num_bytes: 14283483.636363637
    num_examples: 14042
  download_size: 5233340
  dataset_size: 14523284.181818182
- config_name: te_roman
  features:
  - name: answer
    dtype: int64
  - name: language
    dtype: string
  - name: question
    dtype: string
  - name: choices
    sequence: string
  splits:
  - name: test
    num_bytes: 6365080
    num_examples: 13989
  download_size: 3407740
  dataset_size: 6365080
configs:
- config_name: bn
  data_files:
  - split: validation
    path: bn/validation-*
  - split: test
    path: bn/test-*
- config_name: bn_roman
  data_files:
  - split: test
    path: bn_roman/test-*
- config_name: en
  data_files:
  - split: validation
    path: en/validation-*
  - split: test
    path: en/test-*
- config_name: gu
  data_files:
  - split: validation
    path: gu/validation-*
  - split: test
    path: gu/test-*
- config_name: gu_roman
  data_files:
  - split: test
    path: gu_roman/test-*
- config_name: hi
  data_files:
  - split: validation
    path: hi/validation-*
  - split: test
    path: hi/test-*
- config_name: hi_roman
  data_files:
  - split: test
    path: hi_roman/test-*
- config_name: kn
  data_files:
  - split: validation
    path: kn/validation-*
  - split: test
    path: kn/test-*
- config_name: kn_roman
  data_files:
  - split: test
    path: kn_roman/test-*
- config_name: ml
  data_files:
  - split: validation
    path: ml/validation-*
  - split: test
    path: ml/test-*
- config_name: ml_roman
  data_files:
  - split: test
    path: ml_roman/test-*
- config_name: mr
  data_files:
  - split: validation
    path: mr/validation-*
  - split: test
    path: mr/test-*
- config_name: mr_roman
  data_files:
  - split: test
    path: mr_roman/test-*
- config_name: or
  data_files:
  - split: validation
    path: or/validation-*
  - split: test
    path: or/test-*
- config_name: or_roman
  data_files:
  - split: test
    path: or_roman/test-*
- config_name: pa
  data_files:
  - split: validation
    path: pa/validation-*
  - split: test
    path: pa/test-*
- config_name: pa_roman
  data_files:
  - split: test
    path: pa_roman/test-*
- config_name: ta
  data_files:
  - split: validation
    path: ta/validation-*
  - split: test
    path: ta/test-*
- config_name: ta_roman
  data_files:
  - split: test
    path: ta_roman/test-*
- config_name: te
  data_files:
  - split: validation
    path: te/validation-*
  - split: test
    path: te/test-*
- config_name: te_roman
  data_files:
  - split: test
    path: te_roman/test-*
---

# Indic MMLU Dataset

A multilingual version of the [Massive Multitask Language Understanding (MMLU) benchmark](https://huggingface.co/datasets/cais/mmlu), translated from English into 10 Indian languages.
This version contains the translations of the development and test sets only. 

### Languages Covered
The dataset includes translations in the following languages:
- Bengali (bn)
- Gujarati (gu)
- Hindi (hi)
- Kannada (kn)
- Marathi (mr)
- Malayalam (ml)
- Oriya (or)
- Punjabi (pa)
- Tamil (ta)
- Telugu (te)

### Task Format
Each example is a multiple-choice question containing:
- `question`: Question text in target language
- `choices`: List of four possible answers (A, B, C, D) in target language
- `answer`: Correct answer index (0-3)
- `language`: ISO 639-1 language code

## Dataset Statistics
- Validation (dev in the original): ~280 examples per language
- Test: ~14k examples per language

## Usage
```python
from datasets import load_dataset

# we do not maintain subject groupings
dataset = load_dataset("sarvamai/mmlu-indic")
```

## Known Limitations
- Technical terminology may be challenging to translate precisely
- Some subjects (like US Law) may have concepts without direct equivalents
- Cultural and educational system differences may affect question relevance

## License
This dataset follows the same license as the original MMLU dataset.

## Acknowledgments
- Original MMLU dataset creators.