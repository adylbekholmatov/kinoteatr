using System;
using System.Collections.Generic;
using System.IO;
using System.Management;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using OpenCvSharp;
using OpenCvSharp.WpfExtensions;
using ZXing;

namespace AKICinemaAdmin.Views;

public partial class ScanTicketPage : Page
{
    private VideoCapture? _capture;
    private CancellationTokenSource? _cts;
    private bool _cameraOn;
    private bool _suppressCameraChange;
    private string _lastScanned = "";
    private DateTime _lastScanTime = DateTime.MinValue;

    private readonly BarcodeReaderGeneric _reader = new()
    {
        AutoRotate = true,
        Options = new ZXing.Common.DecodingOptions
        {
            TryHarder = true,
            PossibleFormats = new[] { BarcodeFormat.QR_CODE },
        }
    };

    public ScanTicketPage()
    {
        InitializeComponent();
        Unloaded += (_, _) => StopCamera();
        Loaded += (_, _) =>
        {
            LoadCameraList();
            ManualCodeBox.Focus();
        };
    }

    // ── Camera selection ─────────────────────────────────
    // Запомненная камера хранится по имени: индексы сдвигаются при
    // отключении USB-устройства, имя — нет.
    private static readonly string PrefPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "AKICinemaAdmin", "camera.txt");

    private static string LoadPreferredCamera()
    {
        try { return File.Exists(PrefPath) ? File.ReadAllText(PrefPath).Trim() : ""; }
        catch { return ""; }
    }

    private static void SavePreferredCamera(string name)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(PrefPath)!);
            File.WriteAllText(PrefPath, name);
        }
        catch { }
    }

    private static List<string> EnumerateCameras()
    {
        var names = new List<string>();
        foreach (var cls in new[] { "Camera", "Image" })
        {
            try
            {
                using var searcher = new ManagementObjectSearcher(
                    $"SELECT Name FROM Win32_PnPEntity WHERE PNPClass = '{cls}'");
                foreach (var o in searcher.Get())
                {
                    var name = o["Name"]?.ToString();
                    if (!string.IsNullOrWhiteSpace(name) && !names.Contains(name))
                        names.Add(name);
                }
            }
            catch { }
            if (names.Count > 0) break;
        }
        return names;
    }

    private void LoadCameraList()
    {
        var cams = EnumerateCameras();

        _suppressCameraChange = true;
        CameraSelect.ItemsSource = cams;

        if (cams.Count == 0)
        {
            CameraSelect.IsEnabled = false;
            CameraBtn.IsEnabled = false;
            _suppressCameraChange = false;
            return;
        }

        CameraSelect.IsEnabled = true;
        CameraBtn.IsEnabled = true;

        var preferred = LoadPreferredCamera();
        int idx = cams.FindIndex(c => c == preferred);
        CameraSelect.SelectedIndex = idx >= 0 ? idx : 0;
        _suppressCameraChange = false;
    }

    private void RefreshCamerasBtn_Click(object sender, RoutedEventArgs e)
    {
        bool wasOn = _cameraOn;
        if (wasOn) StopCamera();
        LoadCameraList();
        if (wasOn) StartCamera();
    }

    private void CameraSelect_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_suppressCameraChange || CameraSelect.SelectedIndex < 0) return;

        SavePreferredCamera(CameraSelect.SelectedItem?.ToString() ?? "");

        // Переключить на лету, если камера уже работает
        if (_cameraOn)
        {
            StopCamera();
            StartCamera();
        }
    }

    // ── Camera ───────────────────────────────────────────
    private void CameraBtn_Click(object sender, RoutedEventArgs e)
    {
        if (_cameraOn) StopCamera();
        else StartCamera();
    }

    private void StartCamera()
    {
        try
        {
            int index = Math.Max(0, CameraSelect.SelectedIndex);

            // DSHOW: тот же backend, в порядке которого перечисляет устройства Windows,
            // поэтому позиция в списке совпадает с индексом камеры.
            _capture = new VideoCapture(index, VideoCaptureAPIs.DSHOW);
            if (!_capture.IsOpened())
            {
                var name = CameraSelect.SelectedItem?.ToString() ?? "выбранная камера";
                MessageBox.Show($"Не удалось открыть «{name}».\n\n" +
                                "Камера может быть занята другой программой " +
                                "(Zoom, Skype, браузер) или отключена.",
                                "Камера", MessageBoxButton.OK, MessageBoxImage.Warning);
                _capture?.Dispose();
                _capture = null;
                return;
            }

            _capture.Set(VideoCaptureProperties.FrameWidth, 1280);
            _capture.Set(VideoCaptureProperties.FrameHeight, 720);

            _cameraOn = true;
            CameraBtn.Content = "⏸  Выключить камеру";
            CameraPlaceholder.Visibility = Visibility.Collapsed;
            ScanFrame.Visibility = Visibility.Visible;

            _cts = new CancellationTokenSource();
            _ = CaptureLoopAsync(_capture, _cts.Token);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Не удалось открыть камеру: {ex.Message}", "Ошибка",
                            MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void StopCamera()
    {
        // Камеру освобождает сам цикл захвата в finally — иначе при переключении
        // камеры её можно было бы освободить прямо посреди Read().
        _cts?.Cancel();
        _cts = null;
        _cameraOn = false;
        _capture = null;

        if (CameraBtn != null)
        {
            CameraBtn.Content = "▶  Включить камеру";
            CameraPlaceholder.Visibility = Visibility.Visible;
            ScanFrame.Visibility = Visibility.Collapsed;
            CameraImage.Source = null;
        }
    }

    private async Task CaptureLoopAsync(VideoCapture capture, CancellationToken token)
    {
        using var frame = new Mat();

        try
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    if (!capture.Read(frame) || frame.Empty())
                    {
                        await Task.Delay(50, token);
                        continue;
                    }

                    var bitmap = frame.ToBitmapSource();
                    bitmap.Freeze();
                    Dispatcher.Invoke(() =>
                    {
                        if (!token.IsCancellationRequested) CameraImage.Source = bitmap;
                    });

                    TryDecodeFrame(frame);
                    await Task.Delay(80, token);
                }
                catch (OperationCanceledException) { break; }
                catch { await Task.Delay(200, CancellationToken.None); }
            }
        }
        finally
        {
            capture.Release();
            capture.Dispose();
        }
    }

    private void TryDecodeFrame(Mat frame)
    {
        // Debounce: не сканировать тот же код чаще раза в 3 секунды
        if ((DateTime.Now - _lastScanTime).TotalSeconds < 3) return;

        using var gray = new Mat();
        Cv2.CvtColor(frame, gray, ColorConversionCodes.BGR2GRAY);

        var luminance = new ZXing.RGBLuminanceSource(
            MatToRgbBytes(frame), frame.Width, frame.Height,
            ZXing.RGBLuminanceSource.BitmapFormat.BGR24);

        var result = _reader.Decode(luminance);
        if (result == null || string.IsNullOrWhiteSpace(result.Text)) return;

        if (result.Text == _lastScanned && (DateTime.Now - _lastScanTime).TotalSeconds < 10) return;

        _lastScanned = result.Text;
        _lastScanTime = DateTime.Now;

        Dispatcher.Invoke(async () => await VerifyAsync(result.Text));
    }

    private static byte[] MatToRgbBytes(Mat mat)
    {
        var bytes = new byte[mat.Width * mat.Height * 3];
        System.Runtime.InteropServices.Marshal.Copy(mat.Data, bytes, 0, bytes.Length);
        return bytes;
    }

    // ── Manual entry ─────────────────────────────────────
    private async void ManualCodeBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) await VerifyFromInputAsync();
    }

    private async void CheckBtn_Click(object sender, RoutedEventArgs e)
        => await VerifyFromInputAsync();

    private async Task VerifyFromInputAsync()
    {
        var code = ManualCodeBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(code)) return;
        await VerifyAsync(code);
        ManualCodeBox.Clear();
    }

    // ── Verification ─────────────────────────────────────
    private async Task VerifyAsync(string qrData)
    {
        var result = await App.Api.VerifyTicketAsync(qrData);
        if (result == null) return;

        IdlePanel.Visibility   = Visibility.Collapsed;
        ResultPanel.Visibility = Visibility.Visible;

        if (!result.Valid)
        {
            ResultIcon.Text  = "❌";
            ResultTitle.Text = "БИЛЕТ НЕДЕЙСТВИТЕЛЕН";
            ResultTitle.Foreground = new SolidColorBrush(Color.FromRgb(239, 68, 68));
            ResultReason.Text = result.Reason;
            ResultBorder.BorderBrush = new SolidColorBrush(Color.FromRgb(239, 68, 68));
            DetailsBox.Visibility = Visibility.Collapsed;
            return;
        }

        if (result.AlreadyUsed)
        {
            ResultIcon.Text  = "⚠️";
            ResultTitle.Text = "БИЛЕТ УЖЕ ИСПОЛЬЗОВАН";
            ResultTitle.Foreground = new SolidColorBrush(Color.FromRgb(251, 191, 36));
            ResultReason.Text = $"Вход был зарегистрирован: {result.CheckedInAt}";
            ResultBorder.BorderBrush = new SolidColorBrush(Color.FromRgb(251, 191, 36));
        }
        else
        {
            ResultIcon.Text  = "✅";
            ResultTitle.Text = "ПРОХОД РАЗРЕШЁН";
            ResultTitle.Foreground = new SolidColorBrush(Color.FromRgb(34, 197, 94));
            ResultReason.Text = result.ManualEntry ? "Проверено вручную по коду" : "QR-подпись подтверждена";
            ResultBorder.BorderBrush = new SolidColorBrush(Color.FromRgb(34, 197, 94));
        }

        DetailsBox.Visibility = Visibility.Visible;
        DetMovie.Text      = result.Movie;
        DetTime.Text       = result.ScreeningTime;
        DetHall.Text       = result.Hall;
        DetSeatsCount.Text = $"{result.SeatsCount} " + Plural(result.SeatsCount);
        SeatsList.ItemsSource = result.Seats;
        DetCode.Text       = result.BookingCode;
        DetAmount.Text     = $"Оплачено: {result.TotalAmount} сом";
        DetPhone.Text      = $"Телефон: {result.Phone}";
    }

    private static string Plural(int n)
    {
        if (n % 10 == 1 && n % 100 != 11) return "билет";
        if (n % 10 is >= 2 and <= 4 && (n % 100 < 10 || n % 100 >= 20)) return "билета";
        return "билетов";
    }

    private void ResetBtn_Click(object sender, RoutedEventArgs e)
    {
        ResultPanel.Visibility = Visibility.Collapsed;
        IdlePanel.Visibility   = Visibility.Visible;
        ResultBorder.BorderBrush = (Brush)FindResource("BorderBrush");
        _lastScanned = "";
        _lastScanTime = DateTime.MinValue;
        ManualCodeBox.Focus();
    }
}
