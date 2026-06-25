import base64
import unittest

from throughline_ws.ws_protocol import encode_frame, make_accept_key


class ProtocolTests(unittest.TestCase):
    def test_accept_key_matches_rfc_example(self):
        self.assertEqual(
            make_accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
            "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
        )

    def test_server_text_frame_header_for_small_payload(self):
        frame = encode_frame("hi", mask=False)
        self.assertEqual(frame, b"\x81\x02hi")

    def test_client_frame_is_masked(self):
        frame = encode_frame("hi", mask=True)
        self.assertEqual(frame[0], 0x81)
        self.assertTrue(frame[1] & 0x80)
        self.assertEqual(frame[1] & 0x7F, 2)
        self.assertEqual(len(frame), 2 + 4 + 2)


if __name__ == "__main__":
    unittest.main()
