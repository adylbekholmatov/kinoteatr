using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;
using AKICinemaAdmin.Models;
using Newtonsoft.Json;

namespace AKICinemaAdmin.Services;

public class ApiService
{
    private readonly HttpClient _client;
    private string _baseUrl = "http://127.0.0.1:8000/api";
    private string? _token;

    public bool IsAuthenticated => !string.IsNullOrEmpty(_token);
    public string Username { get; private set; } = "";
    public bool IsStaff { get; private set; }

    public string BaseUrl
    {
        get => _baseUrl.Replace("/api", "");
        set => _baseUrl = value.TrimEnd('/') + "/api";
    }

    public ApiService()
    {
        _client = new HttpClient { Timeout = TimeSpan.FromSeconds(15) };
    }

    private void SetAuthHeader()
    {
        if (_token != null)
            _client.DefaultRequestHeaders.Authorization =
                new AuthenticationHeaderValue("Bearer", _token);
    }

    // ── AUTH ─────────────────────────────────────────────
    public async Task<(bool success, string message)> LoginAsync(string username, string password)
    {
        try
        {
            var body = JsonConvert.SerializeObject(new { username, password });
            var content = new StringContent(body, Encoding.UTF8, "application/json");
            var response = await _client.PostAsync($"{_baseUrl}/token/", content);
            var json = await response.Content.ReadAsStringAsync();

            if (response.IsSuccessStatusCode)
            {
                dynamic? data = JsonConvert.DeserializeObject(json);
                _token = data?.access?.ToString();
                Username = data?.username?.ToString() ?? username;
                IsStaff = (bool)(data?.is_staff ?? false);
                SetAuthHeader();
                return (true, "");
            }
            return (false, "Неверный логин или пароль");
        }
        catch (HttpRequestException)
        {
            return (false, "Сервер недоступен. Проверьте подключение.");
        }
        catch (TaskCanceledException)
        {
            return (false, "Превышено время ожидания.");
        }
        catch (Exception ex)
        {
            return (false, $"Ошибка: {ex.Message}");
        }
    }

    public void Logout()
    {
        _token = null;
        Username = "";
        _client.DefaultRequestHeaders.Authorization = null;
    }

    // ── SCREENINGS ───────────────────────────────────────
    public async Task<List<Screening>> GetScreeningsAsync(DateTime? date = null)
    {
        try
        {
            var d = date ?? DateTime.Today;
            var response = await _client.GetAsync($"{_baseUrl}/screenings/?date={d:yyyy-MM-dd}");
            var json = await response.Content.ReadAsStringAsync();
            if (response.IsSuccessStatusCode)
                return JsonConvert.DeserializeObject<List<Screening>>(json) ?? new();
        }
        catch { }
        return new();
    }

    // ── SEAT MAP ─────────────────────────────────────────
    public async Task<SeatMapResponse?> GetSeatMapAsync(int screeningId)
    {
        try
        {
            var response = await _client.GetAsync($"{_baseUrl}/screenings/{screeningId}/seats/");
            var json = await response.Content.ReadAsStringAsync();
            if (response.IsSuccessStatusCode)
                return JsonConvert.DeserializeObject<SeatMapResponse>(json);
        }
        catch { }
        return null;
    }

    // ── BOOKING ──────────────────────────────────────────
    public async Task<(bool success, BookingResult? result, string error)> CreateBookingAsync(
        int screeningId, List<int> seatIds, string phone, string email = "")
    {
        try
        {
            if (string.IsNullOrWhiteSpace(email))
                email = $"kassa_{DateTime.Now.Ticks}@akicinema.kg";

            var body = JsonConvert.SerializeObject(new
            {
                screening_id = screeningId,
                seat_ids = seatIds,
                email = email,
                phone = phone,
                address = "Касса AKI Cinema"
            });

            var content = new StringContent(body, Encoding.UTF8, "application/json");
            var response = await _client.PostAsync($"{_baseUrl}/bookings/", content);
            var json = await response.Content.ReadAsStringAsync();

            if (response.IsSuccessStatusCode)
            {
                var result = JsonConvert.DeserializeObject<BookingResult>(json);
                return (true, result, "");
            }

            dynamic? err = JsonConvert.DeserializeObject(json);
            return (false, null, err?.error?.ToString() ?? "Ошибка бронирования");
        }
        catch (Exception ex)
        {
            return (false, null, $"Ошибка подключения: {ex.Message}");
        }
    }

    public async Task<BookingDetail?> GetBookingDetailAsync(string code)
    {
        try
        {
            var response = await _client.GetAsync($"{_baseUrl}/bookings/{code}/");
            var json = await response.Content.ReadAsStringAsync();
            if (response.IsSuccessStatusCode)
                return JsonConvert.DeserializeObject<BookingDetail>(json);
        }
        catch { }
        return null;
    }
}
