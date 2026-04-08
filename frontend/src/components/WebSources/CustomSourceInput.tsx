import { Banner, Box, Button, Flex, TextInput } from '@neo4j-ndl/react';
import { CustomInput } from '../../types';
import { useTranslate } from '../../context/TranslationContext';

export default function CustomSourceInput({
  value,
  label,
  placeHolder,
  onChangeHandler,
  submitHandler,
  disabledCheck,
  onCloseHandler,
  id,
  onBlurHandler,
  status,
  setStatus,
  statusMessage,
  isValid,
  isFocused,
  onPasteHandler,
}: CustomInput) {
  const t = useTranslate();
  return (
    <Flex gap='6'>
      {status !== 'unknown' && (
        <Box>
          <Banner
            isCloseable={true}
            description={statusMessage}
            onClose={() => setStatus('unknown')}
            type={status}
            name='Custom Banner'
            className='text-lg font-semibold'
            usage='inline'
          />
        </Box>
      )}
      <Box>
        <div className='w-full inline-block'>
          <TextInput
            htmlAttributes={{
              id: id,
              onBlur: onBlurHandler,
              autoFocus: true,
              onPaste: onPasteHandler,

              onKeyDown: (e) => {
                if (e.code === 'Enter') {
                  submitHandler(value);
                }
              },

              'aria-label': label,
              placeholder: placeHolder,
            }}
            value={value}
            isDisabled={false}
            label={label}
            isFluid={true}
            isRequired={true}
            onChange={onChangeHandler}
            errorText={!isValid && isFocused && t('Please Fill The Valid URL')}
          />
        </div>
      </Box>
      <Flex flexDirection='row' justifyContent='flex-end'>
        <div className='websource-btn-container'>
          <Button
            isDisabled={value.trim() === ''}
            color='neutral'
            fill='outlined'
            onClick={onCloseHandler}
            size='medium'
            className='mr-4'
          >
            {t('Reset')}
          </Button>
          <Button onClick={() => submitHandler(value)} size='medium' isDisabled={disabledCheck}>
            {t('Submit')}
          </Button>
        </div>
      </Flex>
    </Flex>
  );
}
