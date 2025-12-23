# core/utils/mock_stt.py


def mock_transcribe(audio_file) -> str:
    """
    Mock STT - 테스트용 가짜 음성 인식

    Args:
        audio_file: 업로드된 오디오 파일 객체

    Returns:
        str: 변환된 텍스트
    """
    filename = getattr(audio_file, "name", "unknown").lower()

    # 파일명 패턴에 따라 다른 응답 반환
    mock_responses = {
        "test1": "오늘 부산항에서 123호 배 타고 낚시했어요. 갑오징어 5마리, 쭈꾸미 3마리 잡았고, 빨강색이랑 야광핑크 에기 사용했습니다.",
        "test2": "통영항에서 456호 배 타고 낚시했습니다. 갑오징어 10마리 잡았어요. 파랑색 에기 사용했습니다.",
        "test3": "포항항에서 쭈꾸미 7마리 잡았어요. 금색 에기 사용했습니다.",
        "busan": "부산항에서 낚시했어요. 갑오징어 8마리, 쭈꾸미 4마리 잡았습니다. 빨강색 에기 썼어요.",
    }

    # 파일명에 키워드가 포함되어 있으면 해당 응답 반환
    for key, response in mock_responses.items():
        if key in filename:
            print(f"[Mock STT] Mock STT: '{key}' 패턴 감지 → 응답 반환")
            return response

    # 기본 응답
    print("[Mock STT] Mock STT: 기본 응답 반환")
    return "부산항에서 낚시했어요. 갑오징어 3마리 잡았습니다."
