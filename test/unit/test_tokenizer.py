import random
import unittest

import numpy as np
import sentencepiece as spm

from joeynmt.data import load_data
from joeynmt.tokenizers import (
    BasicTokenizer,
    FastBPETokenizer,
    SentencePieceTokenizer,
    SpeechProcessor,
    SubwordNMTTokenizer,
)


class TestTokenizer(unittest.TestCase):

    def setUp(self):
        self.train_path = "test/data/toy/train"
        self.dev_path = "test/data/toy/dev"

        # minimal data config
        self.data_cfg = {
            "task": "MT",
            "train": self.train_path,
            "dev": self.dev_path,
            "src": {
                "lang": "de",
                "level": "word",
                "lowercase": False,
                "max_length": 10,
            },
            "trg": {
                "lang": "en",
                "level": "word",
                "lowercase": False,
                "max_length": 10,
            },
            "dataset_type": "plain",
        }

        # set seed
        seed = 42
        random.seed(seed)
        spm.set_random_generator_seed(seed)

    def testBasicTokenizer(self):
        # first valid example from the training set after filtering
        expected_srcs = {
            "char": "Danke.",
            "word": "David Gallo: Das ist Bill Lange. Ich bin Dave Gallo.",
        }
        expected_trgs = {
            "char": "Thank you.",
            "word": "David Gallo: This is Bill Lange. I'm Dave Gallo.",
        }

        # test all combinations of configuration settings
        for level in ["char", "word"]:
            for lowercase in [True, False]:
                current_cfg = self.data_cfg.copy()
                current_cfg["src"]["level"] = level
                current_cfg["trg"]["level"] = level
                current_cfg["src"]["lowercase"] = lowercase
                current_cfg["trg"]["lowercase"] = lowercase

                _, _, train_data, _, _ = load_data(current_cfg, datasets=["train"])
                for lang in [train_data.src_lang, train_data.src_lang]:
                    tokenizer = train_data.tokenizer[lang]
                    self.assertIs(type(tokenizer), BasicTokenizer)
                    self.assertIs(tokenizer.lowercase, lowercase)
                    self.assertEqual(tokenizer.level, level)

                # check the first example from the training set
                expected_src = expected_srcs[level]
                expected_trg = expected_trgs[level]
                if lowercase:
                    expected_src = expected_src.lower()
                    expected_trg = expected_trg.lower()

                if level == "char":
                    self.assertEqual(train_data.src[191], expected_src)
                    self.assertEqual(train_data.trg[191], expected_trg)

                    comparison_src = list(expected_src.replace(" ", "▁"))
                    comparison_trg = list(expected_trg.replace(" ", "▁"))

                    train_src, train_trg = train_data[191]
                    self.assertEqual(train_src, comparison_src)
                    self.assertEqual(train_trg, comparison_trg)

                else:
                    self.assertEqual(train_data.src[0], expected_src)
                    self.assertEqual(train_data.trg[0], expected_trg)

                    comparison_src = expected_src.split()
                    comparison_trg = expected_trg.split()

                    train_src, train_trg = train_data[0]
                    self.assertEqual(train_src, comparison_src)
                    self.assertEqual(train_trg, comparison_trg)

    def testSentencepieceTokenizer(self):
        cfg = self.data_cfg.copy()
        for side in ["src", "trg"]:
            cfg[side]["max_length"] = 30
            cfg[side]["level"] = "bpe"
            cfg[side]["tokenizer_type"] = "sentencepiece"
            cfg[side]["tokenizer_cfg"] = {"model_file": "test/data/toy/sp200.model"}
            cfg[side]["voc_file"] = "test/data/toy/sp200.txt"

        # 6th example from the training set
        expected = {
            "de": {
                "tokenized": [
                    '▁D', 'er', '▁', 'G', 'r', 'o', 'ß', 'te', 'il', '▁der', '▁E', 'r',
                    'd', 'e', '▁ist', '▁M', 'e', 'er', 'w', 'as', 's', 'er', '.'
                ],
                "dropout": [
                    '▁D', 'er', '▁', 'G', 'r', 'o', 'ß', 't', 'e', 'il', '▁der', '▁E',
                    'r', 'd', 'e', '▁ist', '▁M', 'e', 'er', 'w', 'a', 's', 'se', 'r',
                    '.'
                ],
                "detokenized":
                "Der Großteil der Erde ist Meerwasser.",
            },
            "en": {
                "tokenized": [
                    '▁M', 'o', 'st', '▁of', '▁the', '▁', 'p', 'l', 'an', 'e', 't',
                    '▁is', '▁', 'o', 'c', 'e', 'an', '▁w', 'at', 'er', '.'
                ],
                "dropout": [
                    '▁M', 'o', 'st', '▁of', '▁the', '▁', 'p', 'l', 'an', 'e', 't',
                    '▁is', '▁', 'o', 'c', 'e', 'an', '▁', 'w', 'a', 'te', 'r', '.'
                ],
                "detokenized":
                "Most of the planet is ocean water.",
            }
        }

        _, _, train_data, _, _ = load_data(cfg, datasets=["train"])

        train_src, train_trg = train_data[6]
        for tokenized, lang in [(train_src, train_data.src_lang),
                                (train_trg, train_data.trg_lang)]:
            # check tokenizer
            tokenizer = train_data.tokenizer[lang]
            self.assertIs(type(tokenizer), SentencePieceTokenizer)
            self.assertEqual(tokenizer.level, "bpe")

            # check tokenized sequence
            self.assertEqual(tokenized, expected[lang]['tokenized'])

            # check detokenized sequence
            detokenized = tokenizer.post_process(tokenized)
            self.assertEqual(detokenized, expected[lang]['detokenized'])

            tokenizer.nbest_size = -1
            tokenizer.alpha = 0.8
            dropout = tokenizer(detokenized, is_train=True)
            self.assertEqual(dropout, expected[lang]['dropout'])

    def testSubwordNMTTokenizer(self):
        cfg = self.data_cfg.copy()
        for side in ["src", "trg"]:
            cfg[side]["max_length"] = 30
            cfg[side]["level"] = "bpe"
            cfg[side]["tokenizer_type"] = "subword-nmt"
            cfg[side]["tokenizer_cfg"] = {"codes": "test/data/toy/bpe200.codes"}
            cfg[side]["voc_file"] = "test/data/toy/bpe200.txt"

        # 191st example from the training set
        expected = {
            "de": {
                "tokenized": ['D@@', 'an@@', 'k@@', 'e.'],
                "dropout": ['D@@', 'a@@', 'n@@', 'k@@', 'e@@', '.'],
                "detokenized": "Danke.",
            },
            "en": {
                "tokenized": ['Th@@', 'an@@', 'k', 'y@@', 'ou@@', '.'],
                "dropout": ['T@@', 'ha@@', 'n@@', 'k', 'y@@', 'o@@', 'u@@', '.'],
                "detokenized": "Thank you.",
            }
        }

        _, _, train_data, _, _ = load_data(cfg, datasets=["train"])

        train_src, train_trg = train_data[191]
        for tokenized, lang in [(train_src, train_data.src_lang),
                                (train_trg, train_data.trg_lang)]:
            # check tokenizer
            tokenizer = train_data.tokenizer[lang]
            self.assertIs(type(tokenizer), SubwordNMTTokenizer)
            self.assertEqual(tokenizer.level, "bpe")

            # check tokenized sequence
            self.assertEqual(tokenized, expected[lang]['tokenized'])

            # check detokenized sequence
            detokenized = tokenizer.post_process(tokenized)
            self.assertEqual(detokenized, expected[lang]['detokenized'])

            tokenizer.dropout = 0.8
            dropout = tokenizer(detokenized, is_train=True)
            self.assertEqual(dropout, expected[lang]['dropout'])

    def testFastBPETokenizer(self):
        try:
            cfg = self.data_cfg.copy()
            for side in ["src", "trg"]:
                cfg[side]["max_length"] = 30
                cfg[side]["level"] = "bpe"
                cfg[side]["tokenizer_type"] = "fastbpe"
                cfg[side]["tokenizer_cfg"] = {"codes": "test/data/toy/bpe200.codes"}
                cfg[side]["voc_file"] = "test/data/toy/bpe200.txt"

            # 191st example from the training set
            expected = {
                "de": {
                    "tokenized": ['D@@', 'an@@', 'k@@', 'e.'],
                    "dropout": ['D@@', 'a@@', 'n@@', 'k@@', 'e@@', '.'],
                    "detokenized": "Danke.",
                },
                "en": {
                    "tokenized": ['Th@@', 'an@@', 'k', 'y@@', 'ou@@', '.'],
                    "dropout": ['T@@', 'ha@@', 'n@@', 'k', 'y@@', 'o@@', 'u@@', '.'],
                    "detokenized": "Thank you.",
                }
            }

            _, _, train_data, _, _ = load_data(cfg, datasets=["train"])

            train_src, train_trg = train_data[191]
            for tokenized, lang in [(train_src, train_data.src_lang),
                                    (train_trg, train_data.trg_lang)]:
                # check tokenizer
                tokenizer = train_data.tokenizer[lang]
                self.assertIs(type(tokenizer), FastBPETokenizer)
                self.assertEqual(tokenizer.level, "bpe")

                # check tokenized sequence
                self.assertEqual(tokenized, expected[lang]['tokenized'])

                # check detokenized sequence
                detokenized = tokenizer.post_process(tokenized)
                self.assertEqual(detokenized, expected[lang]['detokenized'])

        except (ImportError, RuntimeError) as e:
            raise unittest.SkipTest(f"{e} Skip.")


class TestSpeechProcessor(unittest.TestCase):

    def setUp(self):

        # minimal data config
        self.data_cfg = {
            "task": "s2t",
            "train": "test/data/speech/test",
            "src": {
                "lang": "en",
                "level": "frame",
                "num_freq": 80,
                "max_length": 500,
                "tokenizer_type": "speech",
                "tokenizer_cfg": {
                    "specaugment": {
                        "freq_mask_n": 1,
                        "freq_mask_f": 5,
                        "time_mask_n": 1,
                        "time_mask_t": 10,
                        "time_mask_p": 1.0,
                    },
                    "cmvn": {
                        "norm_means": True,
                        "norm_vars": True,
                        "before": True,
                    },
                },
            },
            "trg": {
                "lang": "en",
                "level": "char",
                "lowercase": True,
                "max_length": 50,
                "voc_file": "test/data/speech/char.txt"
            },
            "dataset_type": "speech",
        }

        # set seed
        seed = 42
        random.seed(seed)

    def testSpeechProcessor(self):
        current_cfg = self.data_cfg.copy()

        # load speech data
        _, _, train_data, _, _ = load_data(current_cfg, datasets=["train"])

        # check tokenizer
        tokenizer = train_data.tokenizer["src"]
        self.assertIs(type(tokenizer), SpeechProcessor)

        # take one train data point
        train_src, train_trg = train_data[1]

        # src ... spectrogram
        train_src_expected = np.array([
            -1.0788909,
            -1.0076448,
            -1.0421542,
            -1.0393586,
            -1.0239305,
            -0.9921213,
            -0.95107234,
            -0.9340749,
            -0.9119267,
            -0.8962079,
        ])
        np.testing.assert_allclose(train_src[0, :10], train_src_expected, rtol=1e-5)

        # trg ... char sequence
        train_trg_expected = ['p', 'o', 'o', 'r', '▁', 'a', 'l', 'i', 'c', 'e', '!']
        self.assertEqual(train_trg, train_trg_expected)

        # TODO: test specaugment, cmvn
