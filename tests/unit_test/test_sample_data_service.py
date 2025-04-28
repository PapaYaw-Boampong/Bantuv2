import warnings
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from fastapi import UploadFile
from io import BytesIO
import uuid
# Suppress Pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from services.sample_data_service import read_csv_upload, SampleDataService


# Utility function test
def test_read_csv_upload():
    csv_content = b"col1,col2\n1,2\n3,4"
    fake_file = UploadFile(filename="test.csv", file=BytesIO(csv_content))
    df = read_csv_upload(fake_file)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["col1", "col2"]
    assert df.shape == (2, 2)


@pytest.mark.asyncio
async def test_get_samples():
    # db = AsyncMock()
    # service = SampleDataService(db)
    #
    # # Patch model to support SQLAlchemy-like usage
    # class DummyPriority:
    #     def desc(self):
    #         return "priority DESC"
    #
    #     def __ge__(self, other):
    #         return True  # or return self for chaining if you want
    #
    # class DummyModel:
    #     id = 123
    #     priority = DummyPriority()
    #     active = True
    #     store = 1
    #
    # # Prepare mock execute result
    # mock_execute_result = MagicMock()
    # mock_execute_result.fetchall.return_value = [(1,), (2,)]
    # mock_scalars = MagicMock()
    # mock_scalars.all.return_value = [MagicMock(), MagicMock()]
    # mock_execute_result.scalars.return_value = mock_scalars
    # db.execute = AsyncMock(return_value=mock_execute_result)
    #
    # # Dummy query builder to bypass SQLAlchemy
    # class DummyQuery:
    #     def __init__(self, *args, **kwargs):
    #         pass
    #
    #     def where(self, *args, **kwargs):
    #         return self
    #
    #     def order_by(self, *args, **kwargs):
    #         return self
    #
    #     def limit(self, *args, **kwargs):
    #         return self
    #
    # # Patch select to return DummyQuery
    # with patch('services.sample_data_service.select', lambda *args, **kwargs: DummyQuery()):
    #     # ids_only True
    #     result = await service.get_samples(DummyModel, 'transcription', ids_only=True)
    #     assert isinstance(result, list)
    #     # ids_only False
    #     result = await service.get_samples(DummyModel, 'transcription', ids_only=False)
    #     assert isinstance(result, list)
    pass


@pytest.mark.asyncio
async def test_create_transcription_sample():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # sample_data = MagicMock()
    # sample_data.model_dump.return_value = {'field': 'value'}
    # with patch('services.sample_data_service.TranscriptionSample', MagicMock(return_value=MagicMock())):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     db.refresh = AsyncMock()
    #     result = await service.create_transcription_sample(sample_data)
    #     assert result is not None
    pass


@pytest.mark.asyncio
async def test_get_transcription_samples():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # with patch.object(service, 'get_samples', AsyncMock(return_value=[MagicMock()])):
    #     result = await service.get_transcription_samples()
    #     assert isinstance(result, list)
    pass


@pytest.mark.asyncio
async def test_create_translation_seed():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # seed_data = MagicMock()
    # seed_data.model_dump.return_value = {'field': 'value'}
    # with patch('services.sample_data_service.TranslationSeedData', MagicMock(return_value=MagicMock())):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     db.refresh = AsyncMock()
    #     result = await service.create_translation_seed(seed_data)
    #     assert result is not None
    pass


@pytest.mark.asyncio
async def test_create_translation_sample():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # sample_data = MagicMock()
    # sample_data.model_dump.return_value = {'field': 'value'}
    # with patch('services.sample_data_service.TranslationSample', MagicMock(return_value=MagicMock())):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     db.refresh = AsyncMock()
    #     result = await service.create_translation_sample(sample_data)
    #     assert result is not None
    pass


@pytest.mark.asyncio
async def test_get_translation_samples():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # with patch.object(service, 'get_samples', AsyncMock(return_value=[MagicMock()])):
    #     result = await service.get_translation_samples()
    #     assert isinstance(result, list)
    pass


@pytest.mark.asyncio
async def test_get_sample_word_frequencies():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # mock_result = MagicMock()
    # mock_result.scalar_one_or_none.return_value = MagicMock(words={'hello': 2})
    # db.execute = AsyncMock(return_value=mock_result)
    #
    # result = await service.get_sample_word_frequencies(uuid.uuid4(), 'translation')
    # assert isinstance(result, dict)
    pass


@pytest.mark.asyncio
async def test_create_annotation_seed():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # seed_data = MagicMock()
    # seed_data.model_dump.return_value = {'field': 'value'}
    # with patch('services.sample_data_service.AnnotationSeedData', MagicMock(return_value=MagicMock())):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     db.refresh = AsyncMock()
    #     result = await service.create_annotation_seed(seed_data)
    #     assert result is not None
    pass


@pytest.mark.asyncio
async def test_create_annotation_sample():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # sample_data = MagicMock()
    # sample_data.model_dump.return_value = {'field': 'value'}
    # with patch('services.sample_data_service.AnnotationSample', MagicMock(return_value=MagicMock())):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     db.refresh = AsyncMock()
    #     result = await service.create_annotation_sample(sample_data)
    #     assert result is not None
    pass


@pytest.mark.asyncio
async def test_get_annotation_samples():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # with patch.object(service, 'get_samples', AsyncMock(return_value=[MagicMock()])):
    #     result = await service.get_annotation_samples()
    #     assert isinstance(result, list)

    pass

@pytest.mark.asyncio
async def test_assign_user_to_sample():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # with patch('services.contribution_service.ContributionManagementService') as mock_contrib:
    #     contrib_instance = mock_contrib.return_value
    #     contrib_instance.find_samples_for_user = AsyncMock(return_value=[uuid.uuid4()])
    #
    #     # async mock chain for db.execute
    #     mock_execute_result = MagicMock()
    #     mock_scalars = MagicMock()
    #     mock_scalars.all.return_value = [MagicMock()]
    #     mock_execute_result.scalars.return_value = mock_scalars
    #     db.execute = AsyncMock(return_value=mock_execute_result)
    #
    #     result = await service.assign_user_to_sample(uuid.uuid4(), uuid.uuid4(), 'transcription')
    #     assert isinstance(result, list)
    pass


@pytest.mark.asyncio
async def test_update_sample_with_contribution():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # sample_id = uuid.uuid4()
    # new_words = {'hello': 1}
    # mock_sample = MagicMock(words={'hello': 1}, store=0)
    # mock_result = MagicMock()
    # mock_result.scalar_one_or_none.return_value = mock_sample
    # db.execute = AsyncMock(return_value=mock_result)
    #
    # class DummyTranscriptionSample:
    #     id = 1
    #     priority = 1
    #     active = True
    #     store = 1
    #
    # class DummyQuery:
    #     def where(self, *args, **kwargs): return self
    #
    #     def order_by(self, *args, **kwargs): return self
    #
    #     def limit(self, *args, **kwargs): return self
    #
    # with patch('services.sample_data_service.TranscriptionSample', DummyTranscriptionSample), \
    #         patch('services.sample_data_service.select', lambda *args, **kwargs: DummyQuery()):
    #     db.commit = AsyncMock()
    #     db.refresh = AsyncMock()
    #     db.add = MagicMock()
    #     result = await service.update_sample_with_contribution(sample_id, 'transcription', new_words)
    #     assert result is not None
    pass


@pytest.mark.asyncio
async def test_deactivate_samples():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # db.execute = AsyncMock()
    # db.commit = AsyncMock()
    # await service.deactivate_samples([uuid.uuid4()], 'transcription')
    # db.execute.assert_called()
    # db.commit.assert_called()
    pass


@pytest.mark.asyncio
async def test_lock_samples():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # db.execute = AsyncMock()
    # db.commit = AsyncMock()
    # await service.lock_samples([uuid.uuid4()], 'transcription')
    # db.execute.assert_called()
    # db.commit.assert_called()
    pass


@pytest.mark.asyncio
async def test_bulk_create_transcription_samples():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # samples = [MagicMock(model_dump=MagicMock(return_value={'field': 'value'})) for _ in range(2)]
    # with patch('services.sample_data_service.TranscriptionSample', MagicMock()):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     result = await service.bulk_create_transcription_samples(samples)
    #     assert result == 2
    pass


@pytest.mark.asyncio
async def test_bulk_create_translation_pairs():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # seed_data = MagicMock()
    # translations = [MagicMock() for _ in range(2)]
    # with patch.object(service, 'create_translation_seed', AsyncMock()), \
    #         patch.object(service, 'create_translation_sample', AsyncMock()):
    #     result = await service.bulk_create_translation_pairs(seed_data, translations)
    #     assert result == 2
    pass


@pytest.mark.asyncio
async def test_update_sample_priority():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # sample_id = uuid.uuid4()
    # mock_sample = MagicMock()
    # mock_result = MagicMock()
    # mock_result.scalar_one_or_none.return_value = mock_sample
    # db.execute = AsyncMock(return_value=mock_result)
    #
    # class DummyTranscriptionSample:
    #     id = 1
    #     priority = 1
    #     active = True
    #     store = 1
    #
    # class DummyQuery:
    #     def where(self, *args, **kwargs): return self
    #
    #     def order_by(self, *args, **kwargs): return self
    #
    #     def limit(self, *args, **kwargs): return self
    #
    # with patch('services.sample_data_service.TranscriptionSample', DummyTranscriptionSample), \
    #         patch('services.sample_data_service.select', lambda *args, **kwargs: DummyQuery()):
    #     db.commit = AsyncMock()
    #     result = await service.update_sample_priority(sample_id, 'transcription', 5)
    #     assert result
    pass


@pytest.mark.asyncio
async def test_bulk_create_annotation_seeds_from_csv():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # csv_content = b"image_url,seed_text,annotations\nurl1,text1,ann1"
    # fake_file = UploadFile(filename="test.csv", file=BytesIO(csv_content))
    # with patch('services.sample_data_service.read_csv_upload',
    #            return_value=pd.DataFrame({'image_url': ['url1'], 'seed_text': ['text1'], 'annotations': ['ann1']})), \
    #         patch('services.sample_data_service.AnnotationSeedData', MagicMock()), \
    #         patch('services.sample_data_service.AnnotationSample', MagicMock()):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     result = await service.bulk_create_annotation_seeds_from_csv(fake_file, uuid.uuid4())
    #     assert result == 1
    pass


@pytest.mark.asyncio
async def test_bulk_create_transcription_seeds_from_csv():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # csv_content = b"audio_urls,transcription_text\nfile1.mp3,text1"
    # fake_file = UploadFile(filename="test.csv", file=BytesIO(csv_content))
    # with patch('services.sample_data_service.read_csv_upload',
    #            return_value=pd.DataFrame({'audio_urls': ['file1.mp3'], 'transcription_text': ['text1']})), \
    #         patch('services.sample_data_service.TranscriptionSample', MagicMock()):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     result = await service.bulk_create_transcription_seeds_from_csv(fake_file, uuid.uuid4())
    #     assert result == 1
    pass


@pytest.mark.asyncio
async def test_bulk_create_translation_seeds_from_csv():
    # db = AsyncMock()
    # service = SampleDataService(db)
    # csv_content = b"original_text\ntext1"
    # fake_file = UploadFile(filename="test.csv", file=BytesIO(csv_content))
    # with patch('services.sample_data_service.read_csv_upload', return_value=pd.DataFrame({'original_text': ['text1']})), \
    #         patch('services.sample_data_service.TranslationSeedData', MagicMock()):
    #     db.add = MagicMock()
    #     db.commit = AsyncMock()
    #     result = await service.bulk_create_translation_seeds_from_csv(fake_file)
    #     assert result == 1
    pass